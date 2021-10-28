#!/usr/bin/env python3
"""
Commands for backfilling content from bulk files into postgresql and s3 (seaweedfs).

Normally this is done by workers (in sandcrawler_worker.py) consuming from
Kafka feeds, but sometimes we have bulk processing output we want to backfill.
"""

import argparse
import os
import sys

from sandcrawler import *
from sandcrawler.persist import *


def run_cdx(args):
    worker = PersistCdxWorker(
        db_url=args.db_url,
    )
    filter_mimetypes = ["application/pdf"]
    if args.no_mimetype_filter:
        filter_mimetypes = None
    pusher = CdxLinePusher(
        worker,
        args.cdx_file,
        filter_http_statuses=[200, 226],
        filter_mimetypes=filter_mimetypes,
        # allow_octet_stream
        batch_size=200,
    )
    pusher.run()


def run_grobid(args):
    worker = PersistGrobidWorker(
        db_url=args.db_url,
        s3_url=args.s3_url,
        s3_bucket=args.s3_bucket,
        s3_access_key=args.s3_access_key,
        s3_secret_key=args.s3_secret_key,
        s3_only=args.s3_only,
        db_only=args.db_only,
    )
    pusher = JsonLinePusher(
        worker,
        args.json_file,
        batch_size=50,
    )
    pusher.run()


def run_grobid_disk(args):
    """
    Writes XML to individual files on disk, and also prints non-XML metadata to
    stdout as JSON, which can be redirected to a separate file.
    """
    worker = PersistGrobidDiskWorker(
        output_dir=args.output_dir,
    )
    pusher = JsonLinePusher(
        worker,
        args.json_file,
    )
    pusher.run()


def run_pdftrio(args):
    worker = PersistPdfTrioWorker(
        db_url=args.db_url,
    )
    pusher = JsonLinePusher(
        worker,
        args.json_file,
        batch_size=100,
    )
    pusher.run()


def run_pdftext(args):
    worker = PersistPdfTextWorker(
        db_url=args.db_url,
        s3_url=args.s3_url,
        s3_bucket=args.s3_bucket,
        s3_access_key=args.s3_access_key,
        s3_secret_key=args.s3_secret_key,
        s3_only=args.s3_only,
        db_only=args.db_only,
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


def run_ingest_request(args):
    worker = PersistIngestRequestWorker(
        db_url=args.db_url,
    )
    pusher = JsonLinePusher(
        worker,
        args.json_file,
        batch_size=200,
    )
    pusher.run()


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--db-url",
        help="postgresql database connection string",
        default="postgres:///sandcrawler",
    )
    parser.add_argument("--s3-url", help="S3 (seaweedfs) backend URL", default="localhost:9000")
    parser.add_argument(
        "--s3-access-key",
        help="S3 (seaweedfs) credential",
        default=os.environ.get("SANDCRAWLER_BLOB_ACCESS_KEY")
        or os.environ.get("MINIO_ACCESS_KEY"),
    )
    parser.add_argument(
        "--s3-secret-key",
        help="S3 (seaweedfs) credential",
        default=os.environ.get("SANDCRAWLER_BLOB_ACCESS_KEY")
        or os.environ.get("MINIO_SECRET_KEY"),
    )
    parser.add_argument(
        "--s3-bucket", help="S3 (seaweedfs) bucket to persist into", default="sandcrawler-dev"
    )
    subparsers = parser.add_subparsers()

    sub_cdx = subparsers.add_parser("cdx", help="backfill a CDX file into postgresql cdx table")
    sub_cdx.set_defaults(func=run_cdx)
    sub_cdx.add_argument(
        "cdx_file",
        help="CDX file to import from (or '-' for stdin)",
        type=argparse.FileType("r"),
    )
    sub_cdx.add_argument(
        "--no-mimetype-filter",
        action="store_true",
        help="ignore mimetype filtering; insert all content types (eg, assuming pre-filtered)",
    )

    sub_grobid = subparsers.add_parser(
        "grobid", help="backfill a grobid JSON ('pg') dump into postgresql and s3 (seaweedfs)"
    )
    sub_grobid.set_defaults(func=run_grobid)
    sub_grobid.add_argument(
        "json_file",
        help="grobid file to import from (or '-' for stdin)",
        type=argparse.FileType("r"),
    )
    sub_grobid.add_argument(
        "--s3-only",
        action="store_true",
        help="only upload TEI-XML to S3 (don't write to database)",
    )
    sub_grobid.add_argument(
        "--db-only",
        action="store_true",
        help="only write status to sandcrawler-db (don't save TEI-XML to S3)",
    )

    sub_pdftext = subparsers.add_parser(
        "pdftext", help="backfill a pdftext JSON ('pg') dump into postgresql and s3 (seaweedfs)"
    )
    sub_pdftext.set_defaults(func=run_pdftext)
    sub_pdftext.add_argument(
        "json_file",
        help="pdftext file to import from (or '-' for stdin)",
        type=argparse.FileType("r"),
    )
    sub_pdftext.add_argument(
        "--s3-only",
        action="store_true",
        help="only upload TEI-XML to S3 (don't write to database)",
    )
    sub_pdftext.add_argument(
        "--db-only",
        action="store_true",
        help="only write status to sandcrawler-db (don't save TEI-XML to S3)",
    )

    sub_grobid_disk = subparsers.add_parser(
        "grobid-disk", help="dump GRBOID output to (local) files on disk"
    )
    sub_grobid_disk.set_defaults(func=run_grobid_disk)
    sub_grobid_disk.add_argument(
        "json_file",
        help="grobid file to import from (or '-' for stdin)",
        type=argparse.FileType("r"),
    )
    sub_grobid_disk.add_argument("output_dir", help="base directory to output into", type=str)

    sub_pdftrio = subparsers.add_parser(
        "pdftrio", help="backfill a pdftrio JSON ('pg') dump into postgresql and s3 (seaweedfs)"
    )
    sub_pdftrio.set_defaults(func=run_pdftrio)
    sub_pdftrio.add_argument(
        "json_file",
        help="pdftrio file to import from (or '-' for stdin)",
        type=argparse.FileType("r"),
    )

    sub_ingest_file_result = subparsers.add_parser(
        "ingest-file-result", help="backfill a ingest_file_result JSON dump into postgresql"
    )
    sub_ingest_file_result.set_defaults(func=run_ingest_file_result)
    sub_ingest_file_result.add_argument(
        "json_file",
        help="ingest_file_result file to import from (or '-' for stdin)",
        type=argparse.FileType("r"),
    )

    sub_ingest_request = subparsers.add_parser(
        "ingest-request", help="backfill a ingest_request JSON dump into postgresql"
    )
    sub_ingest_request.set_defaults(func=run_ingest_request)
    sub_ingest_request.add_argument(
        "json_file",
        help="ingest_request to import from (or '-' for stdin)",
        type=argparse.FileType("r"),
    )

    args = parser.parse_args()
    if not args.__dict__.get("func"):
        print("Tell me what to do!", file=sys.stderr)
        sys.exit(-1)

    args.func(args)


if __name__ == "__main__":
    main()
