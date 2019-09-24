#!/usr/bin/env python3
"""
This is a "one-time" tranform helper script for GROBID backfill into
sandcrawler minio and postgresql.

This variant of backfill_grobid.py pushes into the unpaywall bucket of
sandcrawler-minio and doesn't push anything to sandcrawler table in general.
"""

import json, os, sys, collections, io
import base64
import requests
from minio import Minio
import psycopg2
import psycopg2.extras


def b32_hex(s):
    s = s.strip().split()[0].lower()
    if s.startswith("sha1:"):
        s = s[5:]
    if len(s) != 32:
        return s
    return base64.b16encode(base64.b32decode(s.upper())).lower().decode('utf-8')

def stdin_to_minio():
    mc = Minio('localhost:9000',
        access_key=os.environ['MINIO_ACCESS_KEY'],
        secret_key=os.environ['MINIO_SECRET_KEY'],
        secure=False)
    counts = collections.Counter({'total': 0})
    for l in sys.stdin:
        if counts['raw_lines'] > 0 and counts['raw_lines'] % 10000 == 0:
            print("Progress: {}...".format(counts))
        counts['raw_lines'] += 1
        l = l.strip()
        if not l:
            continue
        row = json.loads(l)
        if not row:
            continue
        sha1hex = b32_hex(row['pdf_hash'])
        grobid_xml = row['tei_xml'].encode('utf-8')
        grobid_xml_len = len(grobid_xml)
        grobid_xml = io.BytesIO(grobid_xml)

        key = "grobid/{}/{}/{}.tei.xml".format(
            sha1hex[0:2],
            sha1hex[2:4],
            sha1hex)
        mc.put_object("unpaywall", key, grobid_xml, grobid_xml_len,
            content_type="application/tei+xml",
            metadata=None)
        counts['minio-success'] += 1

    print("Done: {}".format(counts))

if __name__=='__main__':
    stdin_to_minio()
