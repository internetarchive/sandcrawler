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

import sys
import json
import happybase
import mrjob
from mrjob.job import MRJob

NORMAL_MIME = (
    'application/pdf',
    'application/postscript',
    'text/html',
    'text/xml',
    #'application/xml',
)

def normalize_mime(raw):
    raw = raw.lower()
    for norm in NORMAL_MIME:
        if raw.startswith(norm):
            return norm

    # Special cases 
    if raw.startswith('application/xml'):
        return 'text/xml'
    if raw.startswith('application/x-pdf'):
        return 'application/pdf'
    return None

def test_normalize_mime():
    assert normalize_mime("asdf") == None
    assert normalize_mime("application/pdf") == "application/pdf"
    assert normalize_mime("application/pdf+journal") == "application/pdf"
    assert normalize_mime("Application/PDF") == "application/pdf"
    assert normalize_mime("application/p") == None
    assert normalize_mime("application/xml+stuff") == "text/xml"

def transform_line(raw_cdx):

    cdx = raw_cdx.split()
    if len(cdx) < 11:
        return None

    surt = cdx[0]
    dt = cdx[1]
    url = cdx[2]
    mime = normalize_mime(cdx[3])
    http_status = cdx[4]
    if http_status != "200":
        return None
    key = cdx[5]
    c_size = cdx[8]
    offset = cdx[9]
    warc = cdx[10]
    info = dict(surt=surt, dt=dt, url=url, c_size=c_size, offset=offset,
        warc=warc)
    return {'key': key, 'file:mime': mime, 'file:cdx': info}

def test_transform_line():

    raw = "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz"
    correct = {
        'key': "WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G",
        'file:mime': "application/pdf",
        'file:cdx': {
            'surt': "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf",
            'url': "https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf",
            'dt': "20170828233154",
            'warc': "SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz",
            'offset': "931661233",
            'c_size': "210251",
        }
    }

    assert transform_line(raw) == correct
    assert transform_line(raw + "\n") == correct
    assert transform_line(raw + " extra_field") == correct


class MRCDXBackfillHBase(MRJob):

    # CDX lines in
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

        # Allow passthrough for tests
        if 'hb_table' in kwargs:
            self.hb_table = kwargs.pop('hb_table')
        else:
            self.hb_table = None

        super(MRCDXBackfillHBase, self).__init__(*args, **kwargs)

    def mapper_init(self):

        if self.hb_table is None:
            try:
                host = self.options.hbase_host
                hb_conn = happybase.Connection(host=host)
            except Exception as err:
                raise Exception("Couldn't connect to HBase using host: {}".format(host))
            self.hb_table = hb_conn.table(self.options.hbase_table)

        self.mime_filter = ['application/pdf']

    def mapper(self, _, raw_cdx):

        self.increment_counter('lines', 'total')

        if (raw_cdx.startswith(' ') or raw_cdx.startswith('filedesc') or
                raw_cdx.startswith('#')):

            # Skip line
            self.increment_counter('lines', 'invalid')
            return _, status

        info = transform_line(raw_cdx)
        if info is None:
            self.increment_counter('lines', 'invalid')
            return

        if info['file:mime'] not in self.mime_filter:
            self.increment_counter('lines', 'skip')
            return

        key = info.pop('key')
        info['file:cdx'] = json.dumps(info['file:cdx'], sort_keys=True,
            indent=None)

        self.hb_table.put(key, info)
        self.increment_counter('lines', 'success')

        yield _, dict(status="success")

if __name__ == '__main__':
    MRCDXBackfillHBase.run()

