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

import io
import sys
import struct
import requests
import happybase
import mrjob
from mrjob.job import MRJob
from wayback.resource import Resource
from wayback.resource import ArcResource
from wayback.resourcestore import ResourceStore
from gwb.loader import CDXLoaderFactory
from common import parse_cdx_line


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

    def __init__(self, *args, **kwargs):

        # Allow passthrough for tests
        if 'hb_table' in kwargs:
            self.hb_table = kwargs.pop('hb_table')
        else:
            self.hb_table = None

        super(MRExtractCdxGrobid, self).__init__(*args, **kwargs)
        self.mime_filter = ['application/pdf']

    def grobid_fulltext(self, content):
        r = requests.post(self.options.grobid_uri + "/api/processFulltextDocument",
            files={'input': content})
        if r.status_code is not 200:
            # XXX:
            print("FAIL (Grobid: {}): {}".format(r.content.decode('utf8')))
        else:
            # XXX:
            print("SUCCESS: " + debug_line)
        return r.json()

    def mapper_init(self):

        if self.hb_table is None:
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
            self.increment_counter('lines', 'skip')
            return None, dict(status="skip", reason="mimetype")

        # If warc is not item/file.(w)arc.gz form, skip it
        if len(info['file:cdx']['warc'].split('/')) != 2:
            self.increment_counter('lines', 'skip')
            return None, dict(status="skip", reason="WARC path not petabox item/file")

        return info, None

    def extract(self, info):

        # Fetch data from WARCs in petabox
        try:
            rstore = ResourceStore(loaderfactory=CDXLoaderFactory())
            gwb_record = rstore.load_resource(
                info['file:cdx']['warc'],
                info['file:cdx']['offset'],
                info['file:cdx']['c_size'])
        except IOError as ioe:
            # XXX: catch correct error
            self.increment_counter('lines', 'existing')
            return _, dict(status="existing")

        if gwb_record.get_status()[0] != 200:
            self.increment_counter('lines', 'error')
            return _, dict(status="error", reason="non-HTTP-200 WARC content")

        # Submit to GROBID
        content = gwb_record.open_raw_content()
        try:
            grobid_result = self.grobid_fulltext(gwb_record.open_raw_content())
        except IOError as ioe:
            # XXX: catch correct error
            self.increment_counter('lines', 'existing')
            return _, dict(status="existing")

        info['file:size'] = len(resource_data)

        info['grobid0:status_code'] = None
        info['grobid0:quality'] = None
        info['grobid0:status'] = {}
        info['grobid0:tei_xml'] = None
        info['grobid0:tei_json'] = {}
        info['grobid0:metadata'] = {}

        # Convert TEI XML to JSON
        # TODO

        # Determine extraction "quality"
        # TODO

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

        # Check if we've already processed this line
        oldrow = self.hb_table.row(info['key'], columns=['f', 'file',
            'grobid:status_code'])
        if oldrow.get('grobid0:status', None):
            # This file has already been processed; skip it
            self.increment_counter('lines', 'existing')
            yield _, dict(status="existing")
            return

        # Do the extraction
        info, status = self.extract(info)
        if info is None:
            self.increment_counter('lines', status['status'])
            yield _, status
            return

        # Decide what to bother inserting back into HBase
        # Particularly: ('f:c', 'file:mime', 'file:size', 'file:cdx')
        grobid_status = info.get('grobid0:status_code', None)
        for k in info.keys():
            if k in oldrow:
                info.pop(k)

        # Convert fields to binary
        for k in info.keys():
            if k in ('f:c', 'file:cdx', 'grobid0:status', 'grobid0:tei_json',
                    'grobid0:metadata'):
                assert type(info[k]) == dict
                info[k] = json.dumps(info[k], sort_keys=True, indent=None)
            if k in ('file:size', 'grobid0:status_code'):
                # encode as int64 in network byte order
                info[k] = struct.pack('!q', info[k])

        key = info.pop('key')
        self.hb_table.put(key, info)
        self.increment_counter('lines', 'success')

        yield _, dict(status="success", grobid_status=grobid_status)

if __name__ == '__main__':
    MRExtractCdxGrobid.run()

