#!/usr/bin/env python3
"""
Streaming Hadoop script to import extract metadata and body from fulltext (eg,
PDF) files using GROBID. Input is a CDX file; results primarly go to HBase,
with status written to configurable output stream.

Fulltext files are loaded directly from WARC files in petabox, instead of going
through the wayback replay.

Requires:
- happybase
- mrjob
- wayback/GWB libraries
"""

# XXX: some broken MRO thing going on in here due to python3 object wrangling
# in `wayback` library. Means we can't run pylint.
# pylint: skip-file

import xml
import json
import raven
import struct
import requests
import happybase
import mrjob
from mrjob.job import MRJob
import wayback.exception
from wayback.resource import Resource
from wayback.resource import ArcResource
from wayback.resourcestore import ResourceStore
from gwb.loader import CDXLoaderFactory
from common import parse_cdx_line
from grobid2json import teixml2json

# Yep, a global. Gets DSN from `SENTRY_DSN` environment variable
sentry_client = raven.Client()


class MRExtractCdxGrobid(MRJob):

    # CDX lines in; JSON status out
    #HADOOP_INPUT_FORMAT = 'org.apache.hadoop.mapred.lib.NLineInputFormat'
    #INPUT_PROTOCOL = mrjob.protocol.RawProtocol
    INPUT_PROTOCOL = mrjob.protocol.RawValueProtocol
    OUTPUT_PROTOCOL = mrjob.protocol.JSONValueProtocol

    def configure_args(self):
        super(MRExtractCdxGrobid, self).configure_args()

        self.add_passthru_arg('--hbase-table',
                              type=str,
                              default='wbgrp-journal-extract-0-qa',
                              help='HBase table to backfill into (must exist)')
        self.add_passthru_arg('--hbase-host',
                              type=str,
                              default='localhost',
                              help='HBase thrift API host to connect to')
        self.add_passthru_arg('--grobid-uri',
                              type=str,
                              default='http://localhost:8070',
                              help='URI of GROBID API Server')
        self.add_passthru_arg('--warc-uri-prefix',
                              type=str,
                              default='https://archive.org/serve/',
                              help='URI where WARCs can be found')
        self.add_passthru_arg('--force-existing',
                              action="store_true",
                              help='Re-processes (with GROBID) existing lines')

    def __init__(self, *args, **kwargs):
        super(MRExtractCdxGrobid, self).__init__(*args, **kwargs)
        self.mime_filter = ['application/pdf']
        self.hb_table = None

    def grobid_process_fulltext(self, content):
        r = requests.post(self.options.grobid_uri + "/api/processFulltextDocument",
            files={'input': content})
        return r

    def mapper_init(self):

        if self.hb_table:
            return

        sentry_client.tags_context(dict(hbase_table=self.options.hbase_table))
        try:
            host = self.options.hbase_host
            # TODO: make these configs accessible from... mrconf.cfg?
            hb_conn = happybase.Connection(host=host, transport="framed",
                protocol="compact")
        except Exception:
            raise Exception("Couldn't connect to HBase using host: {}".format(host))
        self.hb_table = hb_conn.table(self.options.hbase_table)

    def parse_line(self, raw_cdx):

        if (raw_cdx.startswith(' ') or raw_cdx.startswith('filedesc') or
                raw_cdx.startswith('#')):
            return None, dict(status="invalid", reason="line prefix")

        info = parse_cdx_line(raw_cdx)
        if info is None:
            return None, dict(status="invalid", reason="CDX parse")

        if info['file:mime'] not in self.mime_filter:
            return None, dict(status="skip", reason="mimetype")

        # If warc is not item/file.(w)arc.gz form, skip it
        if len(info['file:cdx']['warc'].split('/')) != 2:
            return None, dict(status="skip", reason="WARC path not petabox item/file")

        return info, None

    def fetch_warc_content(self, warc_path, offset, c_size):
        warc_uri = self.options.warc_uri_prefix + warc_path
        try:
            rstore = ResourceStore(loaderfactory=CDXLoaderFactory())
            gwb_record = rstore.load_resource(warc_uri, offset, c_size)
        except wayback.exception.ResourceUnavailable:
            return None, dict(status="error",
                reason="failed to load file contents from wayback/petabox")

        if gwb_record.get_status()[0] != 200:
            return None, dict(status="error",
                reason="archived HTTP response (WARC) was not 200",
                warc_status=gwb_record.get_status()[0])
        return gwb_record.open_raw_content().read(), None

    def extract(self, info):

        # Fetch data from WARCs in petabox
        original_content, status = self.fetch_warc_content(
            info['file:cdx']['warc'],
            info['file:cdx']['offset'],
            info['file:cdx']['c_size'])
        if status:
            return None, status

        info['file:size'] = len(original_content)

        # Submit to GROBID
        try:
            grobid_response = self.grobid_process_fulltext(original_content)
        except requests.exceptions.ConnectionError:
            return None, dict(status="error", reason="connection to GROBID worker")

        info['grobid0:status_code'] = grobid_response.status_code
        if grobid_response.status_code != 200:
            # response.text is .content decoded as utf-8
            info['grobid0:status'] = dict(description=grobid_response.text)
            return info, dict(status="error", reason="non-200 GROBID HTTP status",
                extra=grobid_response.text)

        info['grobid0:status'] = {'status': 'success'}
        info['grobid0:tei_xml'] = grobid_response.content

        # Convert TEI XML to JSON
        try:
            info['grobid0:tei_json'] = teixml2json(grobid_response.content, encumbered=True)
        except xml.etree.ElementTree.ParseError:
            return info, dict(status="fail", reason="GROBID 200 XML parse error")
        except ValueError:
            return info, dict(status="fail", reason="GROBID 200 XML non-TEI content")

        tei_metadata = info['grobid0:tei_json'].copy()
        for k in ('body', 'annex'):
            # Remove fulltext (copywritted) content
            tei_metadata.pop(k, None)
        info['grobid0:metadata'] = tei_metadata

        # Determine extraction "quality"
        # TODO:

        info['grobid0:quality'] = None

        return info, None

    @sentry_client.capture_exceptions
    def mapper(self, _, raw_cdx):
        """
        1. parse CDX line
        2. check what is already in hbase
          3. fetch data from wayback
          4. submit to GROBID
            5. convert GROBID response to JSON (and metadata)
            6. determine "quality"
          7. push results to hbase
        """

        self.increment_counter('lines', 'total')

        # Parse line and filter down
        info, status = self.parse_line(raw_cdx)
        if info is None:
            self.increment_counter('lines', status['status'])
            yield _, status
            return
        key = info['key']

        # Note: this may not get "cleared" correctly
        sentry_client.extra_context(dict(row_key=key))

        # Check if we've already processed this line
        oldrow = self.hb_table.row(key,
            columns=[b'f:c', b'file', b'grobid0:status_code'])
        if (oldrow.get(b'grobid0:status_code', None) != None
                and not self.options.force_existing):
            # This file has already been processed; skip it
            self.increment_counter('lines', 'existing')
            yield _, dict(status="existing", key=key)
            return

        # Do the extraction
        info, status = self.extract(info)
        if info is None:
            self.increment_counter('lines', status['status'])
            status['key'] = key
            yield _, status
            return
        extraction_status = status

        # Decide what to bother inserting back into HBase
        # Particularly: ('f:c', 'file:mime', 'file:size', 'file:cdx')
        grobid_status_code = info.get('grobid0:status_code', None)
        for k in list(info.keys()):
            if k.encode('utf-8') in oldrow:
                info.pop(k)

        # Convert fields to binary
        for k in list(info.keys()):
            if info[k] is None:
                info.pop(k)
            elif k in ('f:c', 'file:cdx', 'grobid0:status', 'grobid0:tei_json',
                    'grobid0:metadata'):
                assert type(info[k]) == dict
                info[k] = json.dumps(info[k], sort_keys=True, indent=None)
            elif k in ('file:size', 'grobid0:status_code'):
                # encode as int64 in network byte order
                if info[k] != {} and info[k] != None:
                    info[k] = struct.pack('!q', info[k])

        key = info.pop('key')
        self.hb_table.put(key, info)
        self.increment_counter('lines', 'success')

        if extraction_status is not None:
            yield _, dict(status="partial", key=key,
                grobid_status_code=grobid_status_code,
                reason=extraction_status['reason'])
        else:
            yield _, dict(status="success",
                grobid_status_code=grobid_status_code, key=key,
                extra=extraction_status)


if __name__ == '__main__': # pragma: no cover
    MRExtractCdxGrobid.run()
