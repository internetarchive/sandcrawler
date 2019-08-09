#!/usr/bin/env python3
"""
This is a "one-time" tranform helper script for CDX backfill into sandcrawler
postgresql.

Most of this file was copied from '../python/common.py'.
"""

import json, os, sys, collections
import base64
import psycopg2
import psycopg2.extras

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
    assert normalize_mime("asdf") is None
    assert normalize_mime("application/pdf") == "application/pdf"
    assert normalize_mime("application/pdf+journal") == "application/pdf"
    assert normalize_mime("Application/PDF") == "application/pdf"
    assert normalize_mime("application/p") is None
    assert normalize_mime("application/xml+stuff") == "text/xml"
    assert normalize_mime("application/x-pdf") == "application/pdf"
    assert normalize_mime("application/x-html") is None

def b32_hex(s):
    s = s.strip().split()[0].lower()
    if s.startswith("sha1:"):
        s = s[5:]
    if len(s) != 32:
        return s
    return base64.b16encode(base64.b32decode(s.upper())).lower().decode('utf-8')


def parse_cdx_line(raw_cdx):

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
            and http_status == "200" and len(key) == 32 and dt.isdigit()
            and mime != None):
        return None

    if '-' in (surt, dt, url, mime, http_status, key, c_size, offset, warc):
        return None

    # these are the new/specific bits
    sha1 = b32_hex(key)
    return dict(url=url, datetime=dt, sha1hex=sha1, cdx_sha1hex=None, mimetype=mime, warc_path=warc, warc_csize=int(c_size), warc_offset=int(offset))

def insert(cur, batch):
    sql = """
        INSERT INTO
        cdx (url, datetime, sha1hex, mimetype, warc_path, warc_csize, warc_offset)
        VALUES %s
        ON CONFLICT ON CONSTRAINT cdx_pkey DO NOTHING
        RETURNING 1;
    """
    batch = [(d['url'], d['datetime'], d['sha1hex'], d['mimetype'],
              d['warc_path'], d['warc_csize'], d['warc_offset'])
             for d in batch]
    res = psycopg2.extras.execute_values(cur, sql, batch) # fetch=True
    #return len(res)

def stdin_to_pg():
    # no host means it will use local domain socket by default
    conn = psycopg2.connect(database="sandcrawler", user="postgres")
    cur = conn.cursor()
    counts = collections.Counter({'total': 0})
    batch = []
    for l in sys.stdin:
        l = l.strip()
        if counts['raw_lines'] > 0 and counts['raw_lines'] % 10000 == 0:
            print("Progress: {}...".format(counts))
        counts['raw_lines'] += 1
        if not l:
            continue
        info = parse_cdx_line(l)
        if not info:
            continue
        batch.append(info)
        counts['total'] += 1
        if len(batch) >= 1000:
            insert(cur, batch)
            conn.commit()
            #counts['inserted'] += i
            #counts['existing'] += len(batch) - i
            batch = []
            counts['batches'] += 1
    if batch:
        insert(cur, batch)
        #counts['inserted'] += i
        #counts['existing'] += len(batch) - i
        batch = []
    conn.commit()
    cur.close()
    print("Done: {}".format(counts))

if __name__=='__main__':
    stdin_to_pg()
