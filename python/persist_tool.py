#!/usr/bin/env python3

"""
Commands for backfilling content from bulk files into postgresql and minio.

Normally this is done by workers (in sandcrawler_worker.py) consuming from
Kafka feeds, but sometimes we have bulk processing output we want to backfill.
"""

import sys
import argparse
import datetime
import raven

from sandcrawler import *
from sandcrawler.persist import *


def run_cdx(args):
    worker = PersistCdxWorker(
        db_url=args.db_url,
    )
    filter_mimetypes = ['application/pdf']
    if args.no_mimetype_filter:
        filter_mimetypes = None
    pusher = CdxLinePusher(
        worker,
        args.cdx_file,
        filter_http_statuses=[200],
        filter_mimetypes=filter_mimetypes,
        #allow_octet_stream
        batch_size=200,
    )
    pusher.run()

def run_grobid(args):
    worker = PersistGrobidWorker(
        db_url=args.db_url,
    )
    pusher = JsonLinePusher(
        worker,
        args.json_file,
        batch_size=50,
    )
    pusher.run()

def run_ingest_file_result(args):
    worker = PersistIngestFileResultWorker(
        db_url=args.db_url,
    )
    pusher = JsonLinePusher(
        worker,
        args.json_file,
        batch_size=200,
    )
    pusher.run()

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--db-url',
        help="postgresql database connection string",
        default="postgres:///sandcrawler")
    subparsers = parser.add_subparsers()

    sub_cdx = subparsers.add_parser('cdx',
        help="backfill a CDX file into postgresql cdx table")
    sub_cdx.set_defaults(func=run_cdx)
    sub_cdx.add_argument('cdx_file',
        help="CDX file to import from (or '-' for stdin)",
        type=argparse.FileType('r'))
    sub_cdx.add_argument('--no-mimetype-filter',
        action='store_true',
        help="ignore mimetype filtering; insert all content types (eg, assuming pre-filtered)")

    sub_grobid = subparsers.add_parser('grobid',
        help="backfill a grobid JSON ('pg') dump into postgresql and minio")
    sub_grobid.set_defaults(func=run_grobid)
    sub_grobid.add_argument('json_file',
        help="grobid file to import from (or '-' for stdin)",
        type=argparse.FileType('r'))

    sub_ingest_file_result = subparsers.add_parser('ingest-file-result',
        help="backfill a ingest_file_result JSON dump into postgresql")
    sub_ingest_file_result.set_defaults(func=run_ingest_file_result)
    sub_ingest_file_result.add_argument('json_file',
        help="ingest_file_result file to import from (or '-' for stdin)",
        type=argparse.FileType('r'))

    args = parser.parse_args()
    if not args.__dict__.get("func"):
        print("Tell me what to do!", file=sys.stderr)
        sys.exit(-1)

    args.func(args)

if __name__ == '__main__':
    main()
