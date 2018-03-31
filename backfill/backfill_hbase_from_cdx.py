#!/usr/bin/env python3
"""
Streaming Hadoop script to import CDX metadata into the HBase fulltext table,
primarily for URL-agnostic crawl de-duplication. Takes only "fulltext" file
formats.

Requires:
- happybase

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


def run(in_lines, out_lines, status_lines, table, mime_filter=None):

    if mime_filter is None:
        mime_filter = ['application/pdf']
    count_skip = count_invalid = count_fail = count_success = 0

    for raw_cdx in in_lines.readlines():
        if (raw_cdx.startswith(' ') or raw_cdx.startswith('filedesc') or
                raw_cdx.startswith('#')):
            # Skip line
            count_skip += 1
            continue

        info = transform_line(raw_cdx)
        if info is None:
            count_invalid += 1
            continue
        if info['file:mime'] not in mime_filter:
            count_skip += 1
            continue

        key = info.pop('key')
        info['file:cdx'] = json.dumps(info['file:cdx'], sort_keys=True,
            indent=None)
        try:
            table.put(key, info)
            count_success += 1
        except:
            status_lines.write("ERROR\n") # TODO:
            count_fail += 1

    status_lines.write('\n')
    status_lines.write('skip\t{}\n'.format(count_skip))
    status_lines.write('invalid\t{}\n'.format(count_invalid))
    status_lines.write('fail\t{}\n'.format(count_fail))
    status_lines.write('success\t{}\n'.format(count_success))


def test_run():
    
    import io 
    import happybase_mock

    out = io.StringIO()
    status = io.StringIO()
    raw = io.StringIO("""
com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 301 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz
eu,eui,cadmus)/bitstream/handle/1814/36635/rscas_2015_03.pdf;jsessionid=761393014319a39f40d32ae3eb3a853f?sequence=1 20170705062202 http://cadmus.eui.eu/bitstream/handle/1814/36635/RSCAS_2015_03.pdf%3Bjsessionid%3D761393014319A39F40D32AE3EB3A853F?sequence%3D1 application/PDF 200 MPCXVWMUTRUGFP36SLPHKDLY6NGU4S3J - - 854156 328850624 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz
com,pbworks,educ333b)/robots.txt 20170705063311 http://educ333b.pbworks.com/robots.txt text/plain 200 6VAUYENMOU2SK2OWNRPDD6WTQTECGZAD - - 638 398190140 CITESEERX-CRAWL-2017-06-20-20170705062707827-00049-00058-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705063158203-00053-31209~wbgrp-svc284.us.archive.org~8443.warc.gz
""")

    conn = happybase_mock.Connection()
    conn.create_table('wbgrp-journal-extract-test', {'file': {}, 'grobid0': {}})

    table = conn.table('wbgrp-journal-extract-test')
    run(raw, out, status, table)

    print(status.getvalue())

    assert table.row(b'1') == {}
    # HTTP 301
    assert table.row(b'3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ') == {}
    # valid
    assert table.row(b'MPCXVWMUTRUGFP36SLPHKDLY6NGU4S3J') != {}
    # text/plain
    assert table.row(b'6VAUYENMOU2SK2OWNRPDD6WTQTECGZAD') == {}

    row = table.row(b'MPCXVWMUTRUGFP36SLPHKDLY6NGU4S3J')
    assert row[b'file:mime'] == b"application/pdf"
    json.loads(row[b'file:cdx'].decode('utf-8'))

if __name__=="__main__":
    hb = happybase.Connection(host='')
    with hb.connection() as conn:
        table = conn.table('wbgrp-journal-extract-0-qa')
        run(sys.stdin, sys.stdout, sys.stderr, table)

