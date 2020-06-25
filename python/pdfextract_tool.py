#!/usr/bin/env python3

"""
KNOWN ISSUE: thumbnails are not published to kafka in multi-processing mode
"""

import sys
import json
import argparse
import datetime

from grobid2json import teixml2json
from sandcrawler import *


def run_extract_json(args):
    wayback_client = WaybackClient()
    if args.jobs > 1:
        worker = PdfExtractWorker(wayback_client, sink=None, thumbnail_sink=None)
        multi_worker = MultiprocessWrapper(worker, args.sink)
        pusher = JsonLinePusher(multi_worker, args.json_file, batch_size=args.jobs)
    else:
        worker = PdfExtractWorker(wayback_client, sink=args.sink, thumbnail_sink=args.thumbnail_sink)
        pusher = JsonLinePusher(worker, args.json_file)
    pusher.run()

def run_extract_cdx(args):
    wayback_client = WaybackClient()
    if args.jobs > 1:
        worker = PdfExtractWorker(wayback_client, sink=None, thumbnail_sink=None)
        multi_worker = MultiprocessWrapper(worker, args.sink)
        pusher = CdxLinePusher(
            multi_worker,
            args.cdx_file,
            filter_http_statuses=[200, 226],
            filter_mimetypes=['application/pdf'],
            batch_size=args.jobs,
        )
    else:
        worker = PdfExtractWorker(wayback_client, sink=args.sink, thumbnail_sink=args.thumbnail_sink)
        pusher = CdxLinePusher(
            worker,
            args.cdx_file,
            filter_http_statuses=[200, 226],
            filter_mimetypes=['application/pdf'],
        )
    pusher.run()

def run_extract_zipfile(args):
    if args.jobs > 1:
        print("multi-processing: {}".format(args.jobs), file=sys.stderr)
        worker = PdfExtractBlobWorker(sink=None, thumbnail_sink=None)
        multi_worker = MultiprocessWrapper(worker, args.sink, jobs=args.jobs)
        pusher = ZipfilePusher(multi_worker, args.zip_file, batch_size=args.jobs)
    else:
        worker = PdfExtractBlobWorker(sink=args.sink, thumbnail_sink=args.thumbnail_sink)
        pusher = ZipfilePusher(worker, args.zip_file)
    pusher.run()

def run_single(args):
    worker = PdfExtractBlobWorker(sink=args.sink, thumbnail_sink=args.thumbnail_sink)
    with open(args.pdf_file, 'rb') as pdf_file:
        pdf_bytes = pdf_file.read()
    worker.push_record(pdf_bytes)
    worker.finish()
    if args.thumbnail_sink:
        args.thumbnail_sink.finish()



def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--kafka-mode',
        action='store_true',
        help="send output to Kafka (not stdout)")
    parser.add_argument('--kafka-hosts',
        default="localhost:9092",
        help="list of Kafka brokers (host/port) to use")
    parser.add_argument('--kafka-env',
        default="dev",
        help="Kafka topic namespace to use (eg, prod, qa, dev)")
    parser.add_argument('-j', '--jobs',
        default=8, type=int,
        help="parallelism for batch CPU jobs")
    subparsers = parser.add_subparsers()

    sub_extract_json = subparsers.add_parser('extract-json',
        help="for each JSON line with CDX info, fetches PDF and does PDF extraction")
    sub_extract_json.set_defaults(func=run_extract_json)
    sub_extract_json.add_argument('json_file',
        help="JSON file to import from (or '-' for stdin)",
        type=argparse.FileType('r'))

    sub_extract_cdx = subparsers.add_parser('extract-cdx',
        help="for each CDX line, fetches PDF and does PDF extraction")
    sub_extract_cdx.set_defaults(func=run_extract_cdx)
    sub_extract_cdx.add_argument('cdx_file',
        help="CDX file to import from (or '-' for stdin)",
        type=argparse.FileType('r'))

    sub_extract_zipfile = subparsers.add_parser('extract-zipfile',
        help="opens zipfile, iterates over PDF files inside and does PDF extract for each")
    sub_extract_zipfile.set_defaults(func=run_extract_zipfile)
    sub_extract_zipfile.add_argument('zip_file',
        help="zipfile with PDFs to extract",
        type=str)

    sub_single = subparsers.add_parser('single',
        help="opens single PDF and extracts it")
    sub_single.set_defaults(func=run_single)
    sub_single.add_argument('pdf_file',
        help="single PDF to extract",
        type=str)

    args = parser.parse_args()
    if not args.__dict__.get("func"):
        print("tell me what to do!", file=sys.stderr)
        sys.exit(-1)

    args.text_sink = None
    args.thumbnail_sink = None
    if args.kafka_mode:
        text_topic = "sandcrawler-{}.pdf-text".format(args.kafka_env)
        thumbnail_topic = "sandcrawler-{}.pdf-thumbnail-180px-jpg".format(args.kafka_env)
        args.sink = KafkaCompressSink(kafka_hosts=args.kafka_hosts,
            produce_topic=text_topic)
        args.thumbnail_sink = KafkaSink(kafka_hosts=args.kafka_hosts,
            produce_topic=thumbnail_topic)
        print("Running in kafka output mode, publishing to {} and {}\n".format(
            text_topic, thumbnail_topic), file=sys.stderr)
    else:
        args.sink = None
        args.thumbnail_sink = None

    args.func(args)

if __name__ == '__main__':
    main()
