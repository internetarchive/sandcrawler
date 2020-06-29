#!/usr/bin/env python3

"""
These are generally for continuously running workers that consume from Kafka.
Outputs might either be pushed back into Kafka, or directly into sandcrawler-db
or minio.
"""

import os
import sys
import argparse
import datetime
import raven

from sandcrawler import *

# Yep, a global. Gets DSN from `SENTRY_DSN` environment variable
try:
    git_sha = raven.fetch_git_sha('..')
except Exception as e:
    git_sha = None
sentry_client = raven.Client(release=git_sha)


def run_grobid_extract(args):
    consume_topic = "sandcrawler-{}.ungrobided-pg".format(args.env)
    produce_topic = "sandcrawler-{}.grobid-output-pg".format(args.env)
    sink = KafkaSink(
        kafka_hosts=args.kafka_hosts,
        produce_topic=produce_topic,
    )
    grobid_client = GrobidClient(
        host_url=args.grobid_host,
    )
    wayback_client = WaybackClient(
        host_url=args.grobid_host,
    )
    worker = GrobidWorker(
        grobid_client=grobid_client,
        wayback_client=wayback_client,
        sink=sink,
    )
    pusher = KafkaJsonPusher(
        worker=worker,
        kafka_hosts=args.kafka_hosts,
        consume_topic=consume_topic,
        group="grobid-extract",
        batch_size=1,
    )
    pusher.run()

def run_pdf_extract(args):
    consume_topic = "sandcrawler-{}.unextracted".format(args.env)
    text_topic = "sandcrawler-{}.pdf-text".format(args.env)
    thumbnail_topic = "sandcrawler-{}.pdf-thumbnail-180px-jpg".format(args.env)
    text_sink = KafkaCompressSink(
        kafka_hosts=args.kafka_hosts,
        produce_topic=text_topic,
    )
    thumbnail_sink = KafkaSink(
        kafka_hosts=args.kafka_hosts,
        produce_topic=thumbnail_topic,
    )
    wayback_client = WaybackClient(
        host_url=args.grobid_host,
    )
    worker = PdfExtractWorker(
        wayback_client=wayback_client,
        sink=text_sink,
        thumbnail_sink=thumbnail_sink,
    )
    pusher = KafkaJsonPusher(
        worker=worker,
        kafka_hosts=args.kafka_hosts,
        consume_topic=consume_topic,
        group="pdf-extract",
        batch_size=1,
        push_timeout_sec=120,
    )
    pusher.run()

def run_persist_grobid(args):
    consume_topic = "sandcrawler-{}.grobid-output-pg".format(args.env)
    worker = PersistGrobidWorker(
        db_url=args.db_url,
        s3_url=args.s3_url,
        s3_bucket=args.s3_bucket,
        s3_access_key=args.s3_access_key,
        s3_secret_key=args.s3_secret_key,
        s3_only=args.s3_only,
        db_only=args.db_only,
    )
    kafka_group = "persist-grobid"
    if args.s3_only:
        kafka_group += "-s3"
    pusher = KafkaJsonPusher(
        worker=worker,
        kafka_hosts=args.kafka_hosts,
        consume_topic=consume_topic,
        group=kafka_group,
        push_batches=True,
        batch_size=25,
    )
    pusher.run()

def run_persist_pdftext(args):
    consume_topic = "sandcrawler-{}.pdf-text".format(args.env)
    worker = PersistPdfTextWorker(
        db_url=args.db_url,
        s3_url=args.s3_url,
        s3_bucket=args.s3_bucket,
        s3_access_key=args.s3_access_key,
        s3_secret_key=args.s3_secret_key,
        s3_only=args.s3_only,
        db_only=args.db_only,
    )
    kafka_group = "persist-pdf-text"
    if args.s3_only:
        kafka_group += "-s3"
    pusher = KafkaJsonPusher(
        worker=worker,
        kafka_hosts=args.kafka_hosts,
        consume_topic=consume_topic,
        group=kafka_group,
        push_batches=True,
        batch_size=25,
    )
    pusher.run()

def run_persist_thumbnail(args):
    consume_topic = "sandcrawler-{}.pdf-thumbnail-180px-jpg".format(args.env)
    worker = PersistThumbnailWorker(
        s3_url=args.s3_url,
        s3_bucket=args.s3_bucket,
        s3_access_key=args.s3_access_key,
        s3_secret_key=args.s3_secret_key,
        s3_extension=".180px.jpg",
        s3_folder="pdf",
    )
    pusher = KafkaJsonPusher(
        worker=worker,
        kafka_hosts=args.kafka_hosts,
        consume_topic=consume_topic,
        group="persist-pdf-thumbnail",
        push_batches=False,
        raw_records=True,
        batch_size=25,
    )
    pusher.run()

def run_persist_pdftrio(args):
    consume_topic = "sandcrawler-{}.pdftrio-output".format(args.env)
    worker = PersistPdfTrioWorker(
        db_url=args.db_url,
    )
    pusher = KafkaJsonPusher(
        worker=worker,
        kafka_hosts=args.kafka_hosts,
        consume_topic=consume_topic,
        group="persist-pdftrio",
        push_batches=True,
        batch_size=100,
    )
    pusher.run()

def run_ingest_file(args):
    if args.bulk:
        consume_group = "sandcrawler-{}-ingest-file-bulk".format(args.env)
        consume_topic = "sandcrawler-{}.ingest-file-requests-bulk".format(args.env)
    else:
        consume_group = "sandcrawler-{}-ingest-file".format(args.env)
        consume_topic = "sandcrawler-{}.ingest-file-requests".format(args.env)
    produce_topic = "sandcrawler-{}.ingest-file-results".format(args.env)
    grobid_topic = "sandcrawler-{}.grobid-output-pg".format(args.env)
    sink = KafkaSink(
        kafka_hosts=args.kafka_hosts,
        produce_topic=produce_topic,
    )
    grobid_sink = KafkaSink(
        kafka_hosts=args.kafka_hosts,
        produce_topic=grobid_topic,
    )
    grobid_client = GrobidClient(
        host_url=args.grobid_host,
    )
    worker = IngestFileWorker(
        grobid_client=grobid_client,
        sink=sink,
        grobid_sink=grobid_sink,
        # don't SPNv2 for --bulk backfill
        try_spn2=not args.bulk,
    )
    pusher = KafkaJsonPusher(
        worker=worker,
        kafka_hosts=args.kafka_hosts,
        consume_topic=consume_topic,
        group=consume_group,
        batch_size=1,
    )
    pusher.run()

def run_persist_ingest_file(args):
    consume_topic = "sandcrawler-{}.ingest-file-results".format(args.env)
    worker = PersistIngestFileResultWorker(
        db_url=args.db_url,
    )
    pusher = KafkaJsonPusher(
        worker=worker,
        kafka_hosts=args.kafka_hosts,
        consume_topic=consume_topic,
        group="persist-ingest",
        push_batches=True,
        batch_size=100,
    )
    pusher.run()

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--kafka-hosts',
        default="localhost:9092",
        help="list of Kafka brokers (host/port) to use")
    parser.add_argument('--env',
        default="dev",
        help="Kafka topic namespace to use (eg, prod, qa, dev)")
    parser.add_argument('--grobid-host',
        default="http://grobid.qa.fatcat.wiki",
        help="GROBID API host/port")
    parser.add_argument('--db-url',
        help="postgresql database connection string",
        default="postgres:///sandcrawler")
    parser.add_argument('--s3-url',
        help="S3 (minio) backend URL",
        default="localhost:9000")
    parser.add_argument('--s3-access-key',
        help="S3 (minio) credential",
        default=os.environ.get('MINIO_ACCESS_KEY'))
    parser.add_argument('--s3-secret-key',
        help="S3 (minio) credential",
        default=os.environ.get('MINIO_SECRET_KEY'))
    parser.add_argument('--s3-bucket',
        help="S3 (minio) bucket to persist into",
        default="sandcrawler-dev")
    subparsers = parser.add_subparsers()

    sub_grobid_extract = subparsers.add_parser('grobid-extract',
        help="daemon that consumes CDX JSON objects from Kafka, uses GROBID to extract XML, pushes to Kafka")
    sub_grobid_extract.set_defaults(func=run_grobid_extract)

    sub_pdf_extract = subparsers.add_parser('pdf-extract',
        help="daemon that consumes CDX JSON objects from Kafka, extracts text and thumbnail, pushes to Kafka")
    sub_pdf_extract.set_defaults(func=run_pdf_extract)

    sub_persist_grobid = subparsers.add_parser('persist-grobid',
        help="daemon that consumes GROBID output from Kafka and pushes to minio and postgres")
    sub_persist_grobid.add_argument('--s3-only',
        action='store_true',
        help="only upload TEI-XML to S3 (don't write to database)")
    sub_persist_grobid.add_argument('--db-only',
        action='store_true',
        help="only write status to database (don't upload TEI-XML to S3)")
    sub_persist_grobid.set_defaults(func=run_persist_grobid)

    sub_persist_pdftext = subparsers.add_parser('persist-pdftext',
        help="daemon that consumes pdftext output from Kafka and pushes to minio and postgres")
    sub_persist_pdftext.add_argument('--s3-only',
        action='store_true',
        help="only upload TEI-XML to S3 (don't write to database)")
    sub_persist_pdftext.add_argument('--db-only',
        action='store_true',
        help="only write status to database (don't upload TEI-XML to S3)")
    sub_persist_pdftext.set_defaults(func=run_persist_pdftext)

    sub_persist_thumbnail = subparsers.add_parser('persist-thumbnail',
        help="daemon that consumes thumbnail output from Kafka and pushes to minio and postgres")
    sub_persist_thumbnail.set_defaults(func=run_persist_thumbnail)

    sub_persist_pdftrio = subparsers.add_parser('persist-pdftrio',
        help="daemon that consumes pdftrio output from Kafka and pushes to postgres")
    sub_persist_pdftrio.set_defaults(func=run_persist_pdftrio)

    sub_ingest_file = subparsers.add_parser('ingest-file',
        help="daemon that consumes requests from Kafka, ingests, pushes results to Kafka")
    sub_ingest_file.add_argument('--bulk',
        action='store_true',
        help="consume from bulk kafka topic (eg, for ingest backfill)")
    sub_ingest_file.set_defaults(func=run_ingest_file)

    sub_persist_ingest_file = subparsers.add_parser('persist-ingest-file',
        help="daemon that consumes ingest-file output from Kafka and pushes to postgres")
    sub_persist_ingest_file.set_defaults(func=run_persist_ingest_file)

    args = parser.parse_args()
    if not args.__dict__.get("func"):
        print("tell me what to do!")
        sys.exit(-1)

    args.func(args)

if __name__ == '__main__':
    main()
