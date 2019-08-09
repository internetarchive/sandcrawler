#!/usr/bin/env python3
"""
This is a "one-time" tranform helper script for CDX backfill into sandcrawler
postgresql.

Most of this file was copied from '../python/common.py'.
"""

import json, os, sys
import base64

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

for l in sys.stdin:
    l = l.strip()
    if not l:
        continue
    info = parse_cdx_line(l)
    if not info:
        continue
    print("\t".join([info['url'], info['datetime'], info['sha1hex'], info['mimetype'], info['warc_path'], str(info['warc_csize']), str(info['warc_offset'])]))

