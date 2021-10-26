#!/usr/bin/env python3
"""
Basically just a copy of grobid_tool.py, but for PDF classification instead of
text extraction.

Example of large parallel run, locally:

cat /srv/sandcrawler/tasks/something.cdx | pv -l | parallel -j30 --pipe ./pdftrio_tool.py --kafka-env prod --kafka-hosts wbgrp-svc263.us.archive.org:9092,wbgrp-svc284.us.archive.org:9092,wbgrp-svc285.us.archive.org:9092 --kafka-mode --pdftrio-host http://localhost:3939 -j0 classify-pdf-json -
"""

import argparse
import sys

from sandcrawler import *


def run_classify_pdf_json(args):
    pdftrio_client = PdfTrioClient(host_url=args.pdftrio_host)
    wayback_client = WaybackClient()
    if args.jobs > 1:
        worker = PdfTrioWorker(pdftrio_client,
                               wayback_client,
                               sink=None,
                               mode=args.pdftrio_mode)
        multi_worker = MultiprocessWrapper(worker, args.sink)
        pusher = JsonLinePusher(multi_worker, args.json_file, batch_size=args.jobs)
    else:
        worker = PdfTrioWorker(pdftrio_client,
                               wayback_client,
                               sink=args.sink,
                               mode=args.pdftrio_mode)
        pusher = JsonLinePusher(worker, args.json_file)
    pusher.run()


def run_classify_pdf_cdx(args):
    pdftrio_client = PdfTrioClient(host_url=args.pdftrio_host)
    wayback_client = WaybackClient()
    if args.jobs > 1:
        worker = PdfTrioWorker(pdftrio_client,
                               wayback_client,
                               sink=None,
                               mode=args.pdftrio_mode)
        multi_worker = MultiprocessWrapper(worker, args.sink)
        pusher = CdxLinePusher(
            multi_worker,
            args.cdx_file,
            filter_http_statuses=[200, 226],
            filter_mimetypes=['application/pdf'],
            batch_size=args.jobs,
        )
    else:
        worker = PdfTrioWorker(pdftrio_client,
                               wayback_client,
                               sink=args.sink,
                               mode=args.pdftrio_mode)
        pusher = CdxLinePusher(
            worker,
            args.cdx_file,
            filter_http_statuses=[200, 226],
            filter_mimetypes=['application/pdf'],
        )
    pusher.run()


def run_classify_pdf_zipfile(args):
    pdftrio_client = PdfTrioClient(host_url=args.pdftrio_host)
    worker = PdfTrioBlobWorker(pdftrio_client, sink=args.sink, mode=args.pdftrio_mode)
    pusher = ZipfilePusher(worker, args.zip_file)
    pusher.run()


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--kafka-mode',
                        action='store_true',
                        help="send output to Kafka (not stdout)")
    parser.add_argument('--kafka-hosts',
                        default="localhost:9092",
                        help="list of Kafka brokers (host/port) to use")
    parser.add_argument('--kafka-env',
                        default="dev",
                        help="Kafka topic namespace to use (eg, prod, qa, dev)")
    parser.add_argument('-j',
                        '--jobs',
                        default=8,
                        type=int,
                        help="parallelism for batch CPU jobs")
    parser.add_argument('--pdftrio-host',
                        default="http://pdftrio.qa.fatcat.wiki",
                        help="pdftrio API host/port")
    parser.add_argument('--pdftrio-mode',
                        default="auto",
                        help="which classification mode to use")
    subparsers = parser.add_subparsers()

    sub_classify_pdf_json = subparsers.add_parser(
        'classify-pdf-json',
        help="for each JSON line with CDX info, fetches PDF and does pdftrio classify_pdfion")
    sub_classify_pdf_json.set_defaults(func=run_classify_pdf_json)
    sub_classify_pdf_json.add_argument('json_file',
                                       help="JSON file to import from (or '-' for stdin)",
                                       type=argparse.FileType('r'))

    sub_classify_pdf_cdx = subparsers.add_parser(
        'classify-pdf-cdx',
        help="for each CDX line, fetches PDF and does pdftrio classify_pdfion")
    sub_classify_pdf_cdx.set_defaults(func=run_classify_pdf_cdx)
    sub_classify_pdf_cdx.add_argument('cdx_file',
                                      help="CDX file to import from (or '-' for stdin)",
                                      type=argparse.FileType('r'))

    sub_classify_pdf_zipfile = subparsers.add_parser(
        'classify-pdf-zipfile',
        help=
        "opens zipfile, iterates over PDF files inside and does pdftrio classify_pdf for each")
    sub_classify_pdf_zipfile.set_defaults(func=run_classify_pdf_zipfile)
    sub_classify_pdf_zipfile.add_argument('zip_file',
                                          help="zipfile with PDFs to classify",
                                          type=str)

    args = parser.parse_args()
    if not args.__dict__.get("func"):
        parser.print_help(file=sys.stderr)
        sys.exit(-1)

    args.sink = None
    if args.kafka_mode:
        produce_topic = "sandcrawler-{}.pdftrio-output".format(args.kafka_env)
        print("Running in kafka output mode, publishing to {}\n".format(produce_topic))
        args.sink = KafkaSink(kafka_hosts=args.kafka_hosts, produce_topic=produce_topic)

    args.func(args)


if __name__ == '__main__':
    main()
