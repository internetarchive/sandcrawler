#!/usr/bin/env python3
"""
These are generally for running one-off tasks from the command line. Output
might go to stdout, or might go to Kafka topic.

Example of large parallel run, locally:

    cat /srv/sandcrawler/tasks/ungrobided.2019-09-23.json         | pv -l | parallel -j30 --pipe         ./grobid_tool.py --kafka-env prod --kafka-hosts wbgrp-svc350.us.archive.org:9092,wbgrp-svc284.us.archive.org:9092,wbgrp-svc285.us.archive.org:9092 --kafka-mode --grobid-host http://localhost:8070 -j0 extract-json -
"""

import argparse
import json
import sys

from grobid_tei_xml import parse_document_xml

from sandcrawler import *
from sandcrawler.grobid import CrossrefRefsWorker


def run_single(args):
    grobid_client = GrobidClient(host_url=args.grobid_host)
    resp = grobid_client.process_fulltext(blob=args.pdf_file.read())
    resp["_metadata"] = grobid_client.metadata(resp)
    print(json.dumps(resp, sort_keys=True))


def run_extract_json(args):
    grobid_client = GrobidClient(host_url=args.grobid_host)
    wayback_client = WaybackClient()
    if args.jobs > 1:
        worker = GrobidWorker(grobid_client, wayback_client, sink=None)
        multi_worker = MultiprocessWrapper(worker, args.sink)
        pusher = JsonLinePusher(multi_worker, args.json_file, batch_size=args.jobs)
    else:
        worker = GrobidWorker(grobid_client, wayback_client, sink=args.sink)
        pusher = JsonLinePusher(worker, args.json_file)
    pusher.run()


def run_extract_cdx(args):
    grobid_client = GrobidClient(host_url=args.grobid_host)
    wayback_client = WaybackClient()
    if args.jobs > 1:
        worker = GrobidWorker(grobid_client, wayback_client, sink=None)
        multi_worker = MultiprocessWrapper(worker, args.sink)
        pusher = CdxLinePusher(
            multi_worker,
            args.cdx_file,
            filter_http_statuses=[200, 226],
            filter_mimetypes=["application/pdf"],
            batch_size=args.jobs,
        )
    else:
        worker = GrobidWorker(grobid_client, wayback_client, sink=args.sink)
        pusher = CdxLinePusher(
            worker,
            args.cdx_file,
            filter_http_statuses=[200, 226],
            filter_mimetypes=["application/pdf"],
        )
    pusher.run()


def run_extract_zipfile(args):
    grobid_client = GrobidClient(host_url=args.grobid_host)
    if args.jobs > 1:
        print("multi-processing: {}".format(args.jobs), file=sys.stderr)
        worker = GrobidBlobWorker(grobid_client, sink=None)
        multi_worker = MultiprocessWrapper(worker, args.sink, jobs=args.jobs)
        pusher = ZipfilePusher(multi_worker, args.zip_file, batch_size=args.jobs)
    else:
        worker = GrobidBlobWorker(grobid_client, sink=args.sink)
        pusher = ZipfilePusher(worker, args.zip_file)
    pusher.run()


def run_transform(args):
    grobid_client = GrobidClient()
    for line in args.json_file:
        if not line.strip():
            continue
        line = json.loads(line)
        if args.metadata_only:
            out = grobid_client.metadata(line)
        else:
            tei_doc = parse_document_xml(line["tei_xml"])
            out = tei_doc.to_legacy_dict()
        if out:
            if "source" in line:
                out["source"] = line["source"]
            print(json.dumps(out))


def run_parse_crossref_refs(args):
    grobid_client = GrobidClient(host_url=args.grobid_host)
    worker = CrossrefRefsWorker(grobid_client, sink=args.sink)
    pusher = JsonLinePusher(worker, args.json_file)
    pusher.run()


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--kafka-mode", action="store_true", help="send output to Kafka (not stdout)"
    )
    parser.add_argument(
        "--kafka-hosts",
        default="localhost:9092",
        help="list of Kafka brokers (host/port) to use",
    )
    parser.add_argument(
        "--kafka-env", default="dev", help="Kafka topic namespace to use (eg, prod, qa, dev)"
    )
    parser.add_argument(
        "-j", "--jobs", default=8, type=int, help="parallelism for batch CPU jobs"
    )
    parser.add_argument(
        "--grobid-host", default="https://grobid.qa.fatcat.wiki", help="GROBID API host/port"
    )
    subparsers = parser.add_subparsers()

    sub_single = subparsers.add_parser("single")
    sub_single.set_defaults(func=run_single)
    sub_single.add_argument(
        "pdf_file",
        help="path to PDF file to process",
        type=argparse.FileType("rb"),
    )

    sub_extract_json = subparsers.add_parser(
        "extract-json",
        help="for each JSON line with CDX info, fetches PDF and does GROBID extraction",
    )
    sub_extract_json.set_defaults(func=run_extract_json)
    sub_extract_json.add_argument(
        "json_file",
        help="JSON file to import from (or '-' for stdin)",
        type=argparse.FileType("r"),
    )

    sub_extract_cdx = subparsers.add_parser(
        "extract-cdx", help="for each CDX line, fetches PDF and does GROBID extraction"
    )
    sub_extract_cdx.set_defaults(func=run_extract_cdx)
    sub_extract_cdx.add_argument(
        "cdx_file",
        help="CDX file to import from (or '-' for stdin)",
        type=argparse.FileType("r"),
    )

    sub_extract_zipfile = subparsers.add_parser(
        "extract-zipfile",
        help="opens zipfile, iterates over PDF files inside and does GROBID extract for each",
    )
    sub_extract_zipfile.set_defaults(func=run_extract_zipfile)
    sub_extract_zipfile.add_argument("zip_file", help="zipfile with PDFs to extract", type=str)

    sub_parse_crossref_refs = subparsers.add_parser(
        "parse-crossref-refs",
        help="reads Crossref metadata records, parses any unstructured refs with GROBID",
    )
    sub_parse_crossref_refs.set_defaults(func=run_parse_crossref_refs)
    sub_parse_crossref_refs.add_argument(
        "json_file",
        help="JSON-L file to process (or '-' for stdin)",
        type=argparse.FileType("r"),
    )

    sub_transform = subparsers.add_parser("transform")
    sub_transform.set_defaults(func=run_transform)
    sub_transform.add_argument(
        "--metadata-only",
        action="store_true",
        help="Only pass through bibliographic metadata, not fulltext",
    )
    sub_transform.add_argument(
        "json_file",
        help="convert TEI-XML to JSON. Input is JSON lines with tei_xml field",
        type=argparse.FileType("r"),
    )

    args = parser.parse_args()
    if not args.__dict__.get("func"):
        parser.print_help(file=sys.stderr)
        sys.exit(-1)

    args.sink = None
    if args.kafka_mode:
        produce_topic = "sandcrawler-{}.grobid-output-pg".format(args.kafka_env)
        print("Running in kafka output mode, publishing to {}\n".format(produce_topic))
        args.sink = KafkaCompressSink(kafka_hosts=args.kafka_hosts, produce_topic=produce_topic)

    args.func(args)


if __name__ == "__main__":
    main()
