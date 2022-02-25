#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
from http.server import HTTPServer

import sentry_sdk

from sandcrawler import GrobidClient, JsonLinePusher, KafkaCompressSink, KafkaSink
from sandcrawler.ingest_file import IngestFileRequestHandler, IngestFileWorker
from sandcrawler.ingest_fileset import IngestFilesetWorker


def run_single_ingest(args):
    request = dict(
        ingest_type=args.ingest_type,
        base_url=args.url,
        ext_ids=dict(doi=args.doi),
        fatcat=dict(release_ident=args.release_id),
    )
    if args.force_recrawl:
        request["force_recrawl"] = True
    if request["ingest_type"] in [
        "dataset",
    ]:
        ingester = IngestFilesetWorker(
            try_spn2=not args.no_spn2,
            ingest_file_result_stdout=True,
        )
    else:
        grobid_client = GrobidClient(
            host_url=args.grobid_host,
        )
        ingester = IngestFileWorker(
            try_spn2=not args.no_spn2,
            html_quick_mode=args.html_quick_mode,
            grobid_client=grobid_client,
        )
    result = ingester.process(request)
    print(json.dumps(result, sort_keys=True))
    return result


def run_requests(args):
    # TODO: switch to using JsonLinePusher
    file_worker = IngestFileWorker(
        try_spn2=not args.no_spn2,
        html_quick_mode=args.html_quick_mode,
    )
    fileset_worker = IngestFilesetWorker(
        try_spn2=not args.no_spn2,
    )
    for line in args.json_file:
        request = json.loads(line.strip())
        if request["ingest_type"] in [
            "dataset",
        ]:
            result = fileset_worker.process(request)
        else:
            result = file_worker.process(request)
        print(json.dumps(result, sort_keys=True))


def run_file_requests_backfill(args):
    """
    Special mode for persisting GROBID and pdfextract results to Kafka, but
    printing ingest result to stdout.

    Can be used to batch re-process known files.
    """
    grobid_topic = "sandcrawler-{}.grobid-output-pg".format(args.kafka_env)
    pdftext_topic = "sandcrawler-{}.pdf-text".format(args.kafka_env)
    thumbnail_topic = "sandcrawler-{}.pdf-thumbnail-180px-jpg".format(args.kafka_env)
    xmldoc_topic = "sandcrawler-{}.xml-doc".format(args.kafka_env)
    htmlteixml_topic = "sandcrawler-{}.html-teixml".format(args.kafka_env)
    grobid_sink = KafkaSink(
        kafka_hosts=args.kafka_hosts,
        produce_topic=grobid_topic,
    )
    grobid_client = GrobidClient(
        host_url=args.grobid_host,
    )
    pdftext_sink = KafkaCompressSink(
        kafka_hosts=args.kafka_hosts,
        produce_topic=pdftext_topic,
    )
    thumbnail_sink = KafkaSink(
        kafka_hosts=args.kafka_hosts,
        produce_topic=thumbnail_topic,
    )
    xmldoc_sink = KafkaSink(
        kafka_hosts=args.kafka_hosts,
        produce_topic=xmldoc_topic,
    )
    htmlteixml_sink = KafkaSink(
        kafka_hosts=args.kafka_hosts,
        produce_topic=htmlteixml_topic,
    )
    worker = IngestFileWorker(
        grobid_client=grobid_client,
        sink=None,
        grobid_sink=grobid_sink,
        thumbnail_sink=thumbnail_sink,
        pdftext_sink=pdftext_sink,
        xmldoc_sink=xmldoc_sink,
        htmlteixml_sink=htmlteixml_sink,
        try_spn2=False,
    )
    pusher = JsonLinePusher(
        worker,
        args.json_file,
    )
    pusher.run()


def run_api(args):
    port = 8083
    print("Listening on localhost:{}".format(port))
    server = HTTPServer(("", port), IngestFileRequestHandler)
    server.serve_forever()


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--enable-sentry",
        action="store_true",
        help="report exceptions to Sentry",
    )
    subparsers = parser.add_subparsers()

    sub_single = subparsers.add_parser("single", help="ingests a single base URL")
    sub_single.set_defaults(func=run_single_ingest)
    sub_single.add_argument(
        "ingest_type", default="pdf", help="type of ingest (pdf, html, etc)"
    )
    sub_single.add_argument(
        "--release-id", help="(optional) existing release ident to match to"
    )
    sub_single.add_argument("--doi", help="(optional) existing release DOI to match to")
    sub_single.add_argument(
        "--force-recrawl",
        action="store_true",
        help="ignore GWB history and use SPNv2 to re-crawl",
    )
    sub_single.add_argument("--no-spn2", action="store_true", help="don't use live web (SPNv2)")
    sub_single.add_argument(
        "--html-quick-mode",
        action="store_true",
        help="don't fetch individual sub-resources, just use CDX",
    )
    sub_single.add_argument("url", help="URL of paper to fetch")
    sub_single.add_argument(
        "--grobid-host", default="https://grobid.qa.fatcat.wiki", help="GROBID API host/port"
    )

    sub_requests = subparsers.add_parser(
        "requests", help="takes a series of ingest requests (JSON, per line) and runs each"
    )
    sub_requests.add_argument(
        "--no-spn2", action="store_true", help="don't use live web (SPNv2)"
    )
    sub_requests.add_argument(
        "--html-quick-mode",
        action="store_true",
        help="don't fetch individual sub-resources, just use CDX",
    )
    sub_requests.set_defaults(func=run_requests)
    sub_requests.add_argument(
        "json_file",
        help="JSON file (request per line) to import from (or stdin)",
        default=sys.stdin,
        type=argparse.FileType("r"),
    )

    sub_api = subparsers.add_parser(
        "api", help="starts a simple HTTP server that processes ingest requests"
    )
    sub_api.set_defaults(func=run_api)
    sub_api.add_argument("--port", help="HTTP port to listen on", default=8033, type=int)

    sub_file_requests_backfill = subparsers.add_parser(
        "file-requests-backfill",
        help="starts a simple HTTP server that processes ingest requests",
    )
    sub_file_requests_backfill.set_defaults(func=run_file_requests_backfill)
    sub_file_requests_backfill.add_argument(
        "json_file",
        help="JSON file (request per line) to import from (or stdin)",
        default=sys.stdin,
        type=argparse.FileType("r"),
    )
    sub_file_requests_backfill.add_argument(
        "--kafka-hosts",
        default="localhost:9092",
        help="list of Kafka brokers (host/port) to use",
    )
    sub_file_requests_backfill.add_argument(
        "--kafka-env", default="dev", help="Kafka topic namespace to use (eg, prod, qa, dev)"
    )
    sub_file_requests_backfill.add_argument(
        "--grobid-host", default="https://grobid.qa.fatcat.wiki", help="GROBID API host/port"
    )

    args = parser.parse_args()
    if not args.__dict__.get("func"):
        parser.print_help(file=sys.stderr)
        sys.exit(-1)

    # configure sentry *after* parsing args
    if args.enable_sentry:
        try:
            GIT_REVISION = (
                subprocess.check_output(["git", "describe", "--always"]).strip().decode("utf-8")
            )
        except Exception:
            print("failed to configure git revision", file=sys.stderr)
            GIT_REVISION = None
        sentry_sdk.init(release=GIT_REVISION, environment=args.env, max_breadcrumbs=10)

    args.func(args)


if __name__ == "__main__":
    main()
