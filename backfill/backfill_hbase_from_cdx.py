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
from datetime import datetime
import happybase
import mrjob
from mrjob.job import MRJob

NORMAL_MIME = (
    'application/pdf',
    'application/postscript',
    'text/html',
    'text/xml',
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
    key = cdx[5]
    c_size = cdx[8]
    offset = cdx[9]
    warc = cdx[10]

    if not (key.isalnum() and c_size.isdigit() and offset.isdigit()
            and http_status == "200" and len(key) == 32 and dt.isdigit()):
        return None

    if '-' in (surt, dt, url, mime, http_status, key, c_size, offset, warc):
        return None

    key = "sha1:{}".format(key)

    info = dict(surt=surt, dt=dt, url=url, c_size=int(c_size),
        offset=int(offset), warc=warc)

    warc_file = warc.split('/')[-1]
    dt_iso = datetime.strptime(dt, "%Y%m%d%H%M%S").isoformat()
    try:
        dt_iso = datetime.strptime(dt, "%Y%m%d%H%M%S").isoformat()
    except:
        return None

    # 'i' intentionally not set
    heritrix = dict(u=url, d=dt_iso, f=warc_file, o=int(offset), c=1)
    return {'key': key, 'file:mime': mime, 'file:cdx': info, 'f:c': heritrix}

def test_transform_line():

    raw = "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz"
    correct = {
        'key': "sha1:WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G",
        'file:mime': "application/pdf",
        'file:cdx': {
            'surt': "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf",
            'url': "https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf",
            'dt': "20170828233154",
            'warc': "SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz",
            'offset': 931661233,
            'c_size': 210251,
        },
        'f:c': {
            'u': "https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf",
            'd': "2017-08-28T23:31:54",
            'f': "SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz",
            'o': 931661233,
            'c': 1,
        }
    }

    assert transform_line(raw) == correct
    assert transform_line(raw + "\n") == correct
    assert transform_line(raw + " extra_field") == correct


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

        # Allow passthrough for tests
        if 'hb_table' in kwargs:
            self.hb_table = kwargs.pop('hb_table')
        else:
            self.hb_table = None

        super(MRCDXBackfillHBase, self).__init__(*args, **kwargs)
        self.mime_filter = ['application/pdf']

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

    def mapper(self, _, raw_cdx):

        self.increment_counter('lines', 'total')

        if (raw_cdx.startswith(' ') or raw_cdx.startswith('filedesc') or
                raw_cdx.startswith('#')):

            # Skip line
            # XXX: tests don't cover this path; need coverage!
            self.increment_counter('lines', 'invalid')
            return _, dict(status="invalid")

        info = transform_line(raw_cdx)
        if info is None:
            self.increment_counter('lines', 'invalid')
            return _, dict(status="invalid")

        if info['file:mime'] not in self.mime_filter:
            self.increment_counter('lines', 'skip')
            return _, dict(status="skip")

        key = info.pop('key')
        info['f:c'] = json.dumps(info['f:c'], sort_keys=True, indent=None)
        info['file:cdx'] = json.dumps(info['file:cdx'], sort_keys=True,
            indent=None)

        self.hb_table.put(key, info)
        self.increment_counter('lines', 'success')

        yield _, dict(status="success")

if __name__ == '__main__':
    MRCDXBackfillHBase.run()

