#!/usr/bin/env python3
"""
This script is used to turn ingest request postgres rows (in JSON export
format) back in to regular ingest request JSON.

The only difference is the name and location of some optional keys.
"""

import argparse
import json
import sys


def transform(row):
    """
    dict-to-dict
    """
    row.pop("created", None)
    extra = row.pop("request", None) or {}
    for k in ("ext_ids", "edit_extra"):
        if k in extra:
            row[k] = extra[k]
    if "release_ident" in extra:
        row["fatcat"] = dict(release_ident=extra["release_ident"])
    return row


def run(args):
    for l in args.json_file:
        if not l.strip():
            continue
        try:
            req = transform(json.loads(l))
        except:
            print(l, file=sys.stderr)
        if args.force_recrawl:
            req["force_recrawl"] = True
        print(json.dumps(req, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "json_file", help="SQL output JSON file to process", type=argparse.FileType("r")
    )
    parser.add_argument(
        "force_recrawl",
        action="store_true",
        help="whether to add recrawl (SPNv2) flag to request",
    )
    subparsers = parser.add_subparsers()

    args = parser.parse_args()

    run(args)


if __name__ == "__main__":
    main()
