#!/usr/bin/env python3
"""
Streaming Hadoop script to import CDX metadata into the HBase fulltext table,
primarily for URL-agnostic crawl de-duplication. Takes only "fulltext" file
formats.

Requires:
- happybase
- mrjob

TODO:
- argparse
- refactor into an object
- tests in separate file
- nose tests
- sentry integration for error reporting
"""

import json
import happybase
import mrjob
from mrjob.job import MRJob
from common import parse_cdx_line


class MRCDXBackfillHBase(MRJob):

    # CDX lines in; JSON status out
    INPUT_PROTOCOL = mrjob.protocol.RawValueProtocol
    OUTPUT_PROTOCOL = mrjob.protocol.JSONValueProtocol

    def configure_args(self):
        super(MRCDXBackfillHBase, self).configure_args()

        self.add_passthru_arg('--hbase-table',
                              type=str,
                              default='wbgrp-journal-extract-0-qa',
                              help='HBase table to backfill into (must exist)')
        self.add_passthru_arg('--hbase-host',
                              type=str,
                              default='localhost',
                              help='HBase thrift API host to connect to')

    def __init__(self, *args, **kwargs):
        super(MRCDXBackfillHBase, self).__init__(*args, **kwargs)
        self.mime_filter = ['application/pdf']
        self.hb_table = None

    def mapper_init(self):

        if self.hb_table:
            return

        try:
            host = self.options.hbase_host
            # TODO: make these configs accessible from... mrconf.cfg?
            hb_conn = happybase.Connection(host=host, transport="framed",
                                           protocol="compact")
        except Exception:
            raise Exception("Couldn't connect to HBase using host: {}".format(host))
        self.hb_table = hb_conn.table(self.options.hbase_table)

    def mapper(self, _, raw_cdx):

        self.increment_counter('lines', 'total')

        if (raw_cdx.startswith(' ') or raw_cdx.startswith('filedesc') or
                raw_cdx.startswith('#')):
            self.increment_counter('lines', 'invalid')
            yield _, dict(status="invalid", reason="line prefix")
            return

        info = parse_cdx_line(raw_cdx)
        if info is None:
            self.increment_counter('lines', 'invalid')
            yield _, dict(status="invalid")
            return

        if info['file:mime'] not in self.mime_filter:
            self.increment_counter('lines', 'skip')
            yield _, dict(status="skip", reason="unwanted mimetype")
            return

        key = info.pop('key')
        info['f:c'] = json.dumps(info['f:c'], sort_keys=True, indent=None)
        info['file:cdx'] = json.dumps(info['file:cdx'],
                                      sort_keys=True, indent=None)

        self.hb_table.put(key, info)
        self.increment_counter('lines', 'success')

        yield _, dict(status="success")

if __name__ == '__main__': # pragma: no cover
    MRCDXBackfillHBase.run()
