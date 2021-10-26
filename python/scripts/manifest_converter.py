#!/usr/bin/env python3
"""
Reads a sqlite3 manifest database (IA 2017 style) and outputs a stream of
"match" JSON objects which can be imported into fatcat with matched_import.py

This was used to convert this manifest:

    https://archive.org/details/ia_papers_manifest_2018-01-25/

to JSON format for fast fatcat importing.
"""

import json
import sqlite3
import sys

# iterate over rows in files metadata...
# 1. select all identified DOIs
#   => filter based on count
# 2. select all file metadata
# 3. output object


def or_none(s):
    if s is None:
        return None
    elif type(s) == str and ((not s) or s == "\\N" or s == "-"):
        return None
    return s


def process_db(db_path):

    db = sqlite3.connect(db_path)

    for row in db.execute("SELECT sha1, mimetype, size_bytes, md5 FROM files_metadata"):
        sha1 = row[0]
        dois = db.execute("SELECT doi FROM files_id_doi WHERE sha1=?", [sha1]).fetchall()
        dois = [d[0] for d in dois]
        if not dois:
            continue
        urls = db.execute("SELECT url, datetime FROM urls WHERE sha1=?", [sha1]).fetchall()
        if not urls:
            continue
        cdx = [dict(url=row[0], dt=row[1]) for row in urls]
        obj = dict(
            sha1=sha1,
            mimetype=or_none(row[1]),
            size=(or_none(row[2]) and int(row[2])),
            md5=or_none(row[3]),
            dois=dois,
            cdx=cdx,
        )
        dois = db.execute("SELECT doi FROM files_id_doi WHERE sha1=?", [sha1])
        print(json.dumps(obj))


if __name__ == "__main__":
    process_db(sys.argv[1])
