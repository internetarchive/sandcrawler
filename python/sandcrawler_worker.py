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
sentry_client = raven.Client()


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
    )
    pusher = KafkaJsonPusher(
        worker=worker,
        kafka_hosts=args.kafka_hosts,
        consume_topic=consume_topic,
        group="persist-grobid",
        push_batches=True,
        batch_size=25,
    )
    pusher.run()

def run_ingest_file(args):
    if args.bulk:
        consume_topic = "sandcrawler-{}.ingest-file-requests-bulk".format(args.env)
    else:
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
    )
    pusher = KafkaJsonPusher(
        worker=worker,
        kafka_hosts=args.kafka_hosts,
        consume_topic=consume_topic,
        group="ingest-file",
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
        help="daemon that consumes CDX JSON objects from Kafka, extracts, pushes to Kafka")
    sub_grobid_extract.set_defaults(func=run_grobid_extract)

    sub_persist_grobid = subparsers.add_parser('persist-grobid',
        help="daemon that consumes GROBID output from Kafka and pushes to minio and postgres")
    sub_persist_grobid.add_argument('--s3-only',
        action='store_true',
        help="only upload TEI-XML to S3 (don't write to database)")
    sub_persist_grobid.set_defaults(func=run_persist_grobid)

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
