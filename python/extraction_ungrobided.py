#!/usr/bin/env python3
"""
Variant of extraction_cdx_grobid which takes a partial metadata list as input
instead of CDX. 

This task list is dumped by another Hadoop job which scans over the HBase table
quickly, which allows this job to skip a (relatively) expensive HBase read
per-row.

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
from http.client import IncompleteRead
from wayback.resourcestore import ResourceStore
from gwb.loader import CDXLoaderFactory

from common import parse_ungrobided_line
from grobid2json import teixml2json

# Yep, a global. Gets DSN from `SENTRY_DSN` environment variable
sentry_client = raven.Client()

# Specific poison-pill rows we should skip
KEY_DENYLIST = (
    'sha1:DLCCSMMVTCCIR6LRXHEQLZ4PWO6NG2YT',    # "failed to guess ARC header format"
)

class MRExtractUnGrobided(MRJob):

    # "ungrobided" TSV lines in; JSON status out
    #HADOOP_INPUT_FORMAT = 'org.apache.hadoop.mapred.lib.NLineInputFormat'
    #INPUT_PROTOCOL = mrjob.protocol.RawProtocol
    INPUT_PROTOCOL = mrjob.protocol.RawValueProtocol
    OUTPUT_PROTOCOL = mrjob.protocol.JSONValueProtocol

    def configure_args(self):
        super(MRExtractUnGrobided, self).configure_args()

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
        super(MRExtractUnGrobided, self).__init__(*args, **kwargs)
        self.hb_table = None
        self.petabox_webdata_secret = kwargs.get('petabox_webdata_secret', os.environ.get('PETABOX_WEBDATA_SECRET'))
        self.mime_filter = ['application/pdf']
        self.rstore = None

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

    def parse_ungrobided_line(self, raw_line):
        """Line should be TSV and have non-null fields:

            - key (string)
            - f:c (string, json)
            - file:mime (string)
            - file:cdx (string, json)
        """

        if (raw_line.startswith(' ') or raw_line.startswith('#')):
            return None, dict(status="invalid", reason="line prefix", input=raw_line)

        info = parse_ungrobided_line(raw_line)
        if info is None:
            return None, dict(status="invalid", reason="ungrobided parse")

        if info['file:mime'] not in self.mime_filter:
            return None, dict(status="skip", reason="mimetype", mimetype=info['file:mime'])

        # If warc is not item/file.(w)arc.gz form, skip it
        if len(info['file:cdx']['warc'].split('/')) != 2:
            return None, dict(status="skip", reason="WARC path not petabox item/file", path=info['file:cdx']['warc'])

        return info, None

    def fetch_warc_content(self, warc_path, offset, c_size):
        warc_uri = self.warc_uri_prefix + warc_path
        if not self.rstore:
            self.rstore = ResourceStore(loaderfactory=CDXLoaderFactory(
                webdata_secret=self.petabox_webdata_secret,
                download_base_url=self.petabox_base_url))
        try:
            gwb_record = self.rstore.load_resource(warc_uri, offset, c_size)
        except wayback.exception.ResourceUnavailable:
            return None, dict(status="error",
                reason="failed to load file contents from wayback/petabox (ResourceUnavailable)")
        except ValueError as ve:
            return None, dict(status="error",
                reason="failed to load file contents from wayback/petabox (ValueError: {})".format(ve))
        except EOFError as eofe:
            return None, dict(status="error",
                reason="failed to load file contents from wayback/petabox (EOFError: {})".format(eofe))
        except TypeError as te:
            return None, dict(status="error",
                reason="failed to load file contents from wayback/petabox (TypeError: {}; likely a bug in wayback python code)".format(te))
        # Note: could consider a generic "except Exception" here, as we get so
        # many petabox errors. Do want jobs to fail loud and clear when the
        # whole cluster is down though.

        if gwb_record.get_status()[0] != 200:
            return None, dict(status="error",
                reason="archived HTTP response (WARC) was not 200",
                warc_status=gwb_record.get_status()[0])

        try:
            raw_content = gwb_record.open_raw_content().read()
        except IncompleteRead as ire:
            return None, dict(status="error",
                reason="failed to read actual file contents from wayback/petabox (IncompleteRead: {})".format(ire))
        return raw_content, None

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

        # 4 MByte XML size limit; don't record GROBID status on this path
        if len(grobid_response.content) > 4000000:
            info['grobid0:status'] = {'status': 'oversize'}
            return info, dict(status="oversize", reason="TEI response was too large")

        if grobid_response.status_code != 200:
            # response.text is .content decoded as utf-8
            info['grobid0:status'] = dict(status='error', description=grobid_response.text)
            return info, dict(status="error", reason="non-200 GROBID HTTP status",
                extra=grobid_response.text)

        info['grobid0:status'] = {'status': 'partial'}
        info['grobid0:tei_xml'] = grobid_response.content

        # Convert TEI XML to JSON
        try:
            info['grobid0:tei_json'] = teixml2json(info['grobid0:tei_xml'], encumbered=True)
        except xml.etree.ElementTree.ParseError:
            info['grobid0:status'] = dict(status="fail", reason="GROBID 200 XML parse error")
            return info, info['grobid0:status']
        except ValueError:
            info['grobid0:status'] = dict(status="fail", reason="GROBID 200 XML non-TEI content")
            return info, info['grobid0:status']

        tei_metadata = info['grobid0:tei_json'].copy()
        for k in ('body', 'annex'):
            # Remove fulltext (copywritted) content
            tei_metadata.pop(k, None)
        info['grobid0:metadata'] = tei_metadata

        # Determine extraction "quality"
        # TODO:

        info['grobid0:quality'] = None
        info['grobid0:status'] = {'status': 'success'}

        return info, None

    @sentry_client.capture_exceptions
    def mapper(self, _, raw_line):
        """
        1. parse filtered line
        2. fetch data from wayback
        3. submit to GROBID
          4. convert GROBID response to JSON (and metadata)
          6. determine "quality"
        6. push results to hbase
        """

        self.increment_counter('lines', 'total')

        # Parse line and filter down
        info, status = self.parse_ungrobided_line(raw_line)
        if info is None:
            self.increment_counter('lines', status['status'])
            yield _, status
            return
        key = info['key']
        if key in KEY_DENYLIST:
            self.increment_counter('lines', 'denylist')
            yield _, dict(status='denylist', key=key)
            return

        # Note: this may not get "cleared" correctly
        sentry_client.extra_context(dict(row_key=key))

        # Do the extraction
        info, status = self.extract(info)
        if info is None:
            self.increment_counter('lines', status['status'])
            status['key'] = key
            yield _, status
            return
        extraction_status = status

        # Decide what to bother inserting back into HBase
        # Basically, don't overwrite backfill fields.
        grobid_status_code = info.get('grobid0:status_code', None)
        for k in list(info.keys()):
            if k in ('f:c', 'file:mime', 'file:cdx'):
                info.pop(k)

        # Convert fields to binary
        for k in list(info.keys()):
            if info[k] is None:
                info.pop(k)
            # NOTE: we're not actually sending these f:*, file:* keys...
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
    MRExtractUnGrobided.run()
