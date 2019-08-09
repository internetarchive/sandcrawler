#!/usr/bin/env python3
"""
This is a "one-time" tranform helper script for file_meta backfill into
sandcrawler postgresql.

Most of this file was copied from '../python/common.py'.
"""

import json, os, sys, collections
import psycopg2
import psycopg2.extras


def insert(cur, batch):
    sql = """
        INSERT INTO
        file_meta
        VALUES %s
        ON CONFLICT DO NOTHING;
    """
    res = psycopg2.extras.execute_values(cur, sql, batch)

def stdin_to_pg():
    # no host means it will use local domain socket by default
    conn = psycopg2.connect(database="sandcrawler", user="postgres")
    cur = conn.cursor()
    counts = collections.Counter({'total': 0})
    batch = []
    for l in sys.stdin:
        if counts['raw_lines'] > 0 and counts['raw_lines'] % 10000 == 0:
            print("Progress: {}...".format(counts))
        counts['raw_lines'] += 1
        if not l.strip():
            continue
        info = l.split("\t")
        if not info:
            continue
        assert len(info) == 5
        info[-1] = info[-1].strip() or None
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
