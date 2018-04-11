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

# XXX: some broken MRO thing going on in here
# pylint: skip-file

import io
import sys
import xml
import json
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


class MRExtractCdxGrobid(MRJob):

    # CDX lines in; JSON status out
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

        try:
            host = self.options.hbase_host
            # TODO: make these configs accessible from... mrconf.cfg?
            hb_conn = happybase.Connection(host=host, transport="framed",
                protocol="compact")
        except Exception as err:
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
        except wayback.exception.ResourceUnavailable as err:
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
        if grobid_response.status_code is not 200:
            # response.text is .content decoded as utf-8
            info['grobid0:status'] = json.loads(grobid_response.text)
            return info, dict(status="error", reason="non-200 GROBID HTTP status",
                extra=grobid_response.content)

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

        # Check if we've already processed this line
        oldrow = self.hb_table.row(key, columns=[b'f', b'file',
            b'grobid0:status_code'])
        if oldrow.get(b'grobid0:status_code', None) != None:
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

        # Decide what to bother inserting back into HBase
        # Particularly: ('f:c', 'file:mime', 'file:size', 'file:cdx')
        grobid_status = info.get('grobid0:status_code', None)
        for k in list(info.keys()):
            if k.encode('utf-8') in oldrow:
                info.pop(k)

        # Convert fields to binary
        for k in list(info.keys()):
            if info[k] == None:
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

        yield _, dict(status="success", grobid_status=grobid_status, key=key)


if __name__ == '__main__': # pragma: no cover
    MRExtractCdxGrobid.run()

