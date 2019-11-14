#!/usr/bin/env python3

"""
These are generally for continuously running workers that consume from Kafka.
Outputs might either be pushed back into Kafka, or directly into sandcrawler-db
or minio.
"""

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
    sink = KafkaSink(kafka_hosts=args.kafka_hosts, produce_topic=produce_topic)
    grobid_client = GrobidClient(host_url=args.grobid_host)
    wayback_client = WaybackClient(host_url=args.grobid_host)
    worker = GrobidWorker(grobid_client=grobid_client, wayback_client=wayback_client, sink=sink)
    pusher = KafkaJsonPusher(worker=worker, kafka_hosts=args.kafka_hosts,
        consume_topic=consume_topic, group="grobid-extract")
    pusher.run()

def run_grobid_persist(args):
    consume_topic = "sandcrawler-{}.grobid-output-pg".format(args.env)
    raise NotImplementedError
    #worker = GrobidPersistWorker()
    #pusher = KafkaJsonPusher(worker=worker, kafka_hosts=args.kafka_hosts,
    #    consume_topic=consume_topic, group="grobid-persist")
    #pusher.run()

def run_ingest_file(args):
    consume_topic = "sandcrawler-{}.ingest-file-requests".format(args.env)
    produce_topic = "sandcrawler-{}.ingest-file-results".format(args.env)
    sink = KafkaSink(kafka_hosts=args.kafka_hosts, produce_topic=produce_topic)
    grobid_client = GrobidClient(host_url=args.grobid_host)
    worker = IngestFileWorker(grobid_client=grobid_client, sink=sink)
    pusher = KafkaJsonPusher(worker=worker, kafka_hosts=args.kafka_hosts,
        consume_topic=consume_topic, group="ingest-file")
    pusher.run()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kafka-hosts',
        default="localhost:9092",
        help="list of Kafka brokers (host/port) to use")
    parser.add_argument('--env',
        default="dev",
        help="Kafka topic namespace to use (eg, prod, qa, dev)")
    parser.add_argument('--grobid-host',
        default="http://grobid.qa.fatcat.wiki",
        help="GROBID API host/port")
    subparsers = parser.add_subparsers()

    sub_grobid_extract = subparsers.add_parser('grobid-extract')
    sub_grobid_extract.set_defaults(func=run_grobid_extract)

    sub_grobid_persist = subparsers.add_parser('grobid-persist')
    sub_grobid_persist.set_defaults(func=run_grobid_persist)

    sub_ingest_file = subparsers.add_parser('ingest-file')
    sub_ingest_file.set_defaults(func=run_ingest_file)

    args = parser.parse_args()
    if not args.__dict__.get("func"):
        print("tell me what to do!")
        sys.exit(-1)

    args.func(args)

if __name__ == '__main__':
    main()
