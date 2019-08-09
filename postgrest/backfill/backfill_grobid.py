#!/usr/bin/env python3
"""
This is a "one-time" tranform helper script for GROBID backfill into
sandcrawler minio and postgresql.
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

def insert(cur, batch):
    sql = """
        INSERT INTO
        grobid (sha1hex, grobid_version, status_code, status, fatcat_release, metadata)
        VALUES %s
        ON CONFLICT DO NOTHING;
    """
    batch = [(d['sha1hex'], d['grobid_version'], d['status_code'], d['status'], d['fatcat_release'], d['metadata'])
             for d in batch]
    res = psycopg2.extras.execute_values(cur, sql, batch)

def stdin_to_pg():
    mc = Minio('localhost:9000',
        access_key=os.environ['MINIO_ACCESS_KEY'],
        secret_key=os.environ['MINIO_SECRET_KEY'],
        secure=False)
    # no host means it will use local domain socket by default
    conn = psycopg2.connect(database="sandcrawler", user="postgres")
    cur = conn.cursor()
    counts = collections.Counter({'total': 0})
    batch = []
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

        key = "{}/{}/{}.tei.xml".format(
            sha1hex[0:2],
            sha1hex[2:4],
            sha1hex)
        mc.put_object("grobid", key, grobid_xml, grobid_xml_len,
            content_type="application/tei+xml",
            metadata=None)
        counts['minio-success'] += 1

        info = dict(
            sha1hex=sha1hex,
            grobid_version=None, # TODO
            status_code=200,
            status=None,
            fatcat_release=None,
            metadata=None,
        )
        batch.append(info)
        counts['total'] += 1
        if len(batch) >= 1000:
            insert(cur, batch)
            conn.commit()
            batch = []
            counts['batches'] += 1
    if batch:
        insert(cur, batch)
        batch = []
    conn.commit()
    cur.close()
    print("Done: {}".format(counts))

if __name__=='__main__':
    stdin_to_pg()
