#!/usr/bin/env python3
"""
These are generally for continuously running workers that consume from Kafka.
Outputs might either be pushed back into Kafka, or directly into sandcrawler-db
or S3 (SeaweedFS).
"""

import argparse
import os
import subprocess
import sys

import sentry_sdk

from sandcrawler import *
from sandcrawler.persist import (
    PersistCrossrefWorker,
    PersistHtmlTeiXmlWorker,
    PersistXmlDocWorker,
)


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
    pdftext_topic = "sandcrawler-{}.pdf-text".format(args.env)
    thumbnail_topic = "sandcrawler-{}.pdf-thumbnail-180px-jpg".format(args.env)
    pdftext_sink = KafkaCompressSink(
        kafka_hosts=args.kafka_hosts,
        produce_topic=pdftext_topic,
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
        sink=pdftext_sink,
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
    if args.kafka_group_suffix:
        kafka_group += args.kafka_group_suffix
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
    if args.kafka_group_suffix:
        kafka_group += args.kafka_group_suffix
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
    kafka_group = "persist-pdf-thumbnail"
    if args.kafka_group_suffix:
        kafka_group += args.kafka_group_suffix
    pusher = KafkaJsonPusher(
        worker=worker,
        kafka_hosts=args.kafka_hosts,
        consume_topic=consume_topic,
        group=kafka_group,
        push_batches=False,
        raw_records=True,
        batch_size=25,
    )
    pusher.run()


def run_persist_xml_doc(args: argparse.Namespace) -> None:
    consume_topic = f"sandcrawler-{args.env}.xml-doc"
    worker = PersistXmlDocWorker(
        s3_url=args.s3_url,
        s3_bucket=args.s3_bucket,
        s3_access_key=args.s3_access_key,
        s3_secret_key=args.s3_secret_key,
    )
    kafka_group = "persist-xml-doc"
    if args.kafka_group_suffix:
        kafka_group += args.kafka_group_suffix
    pusher = KafkaJsonPusher(
        worker=worker,
        kafka_hosts=args.kafka_hosts,
        consume_topic=consume_topic,
        group=kafka_group,
        push_batches=False,
        batch_size=25,
    )
    pusher.run()


def run_persist_html_teixml(args: argparse.Namespace) -> None:
    consume_topic = f"sandcrawler-{args.env}.html-teixml"
    worker = PersistHtmlTeiXmlWorker(
        s3_url=args.s3_url,
        s3_bucket=args.s3_bucket,
        s3_access_key=args.s3_access_key,
        s3_secret_key=args.s3_secret_key,
    )
    kafka_group = "persist-html-teixml"
    if args.kafka_group_suffix:
        kafka_group += args.kafka_group_suffix
    pusher = KafkaJsonPusher(
        worker=worker,
        kafka_hosts=args.kafka_hosts,
        consume_topic=consume_topic,
        group=kafka_group,
        push_batches=False,
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
    spn_cdx_retry_sec = 9.0
    if args.bulk:
        consume_group = "sandcrawler-{}-ingest-file-bulk".format(args.env)
        consume_topic = "sandcrawler-{}.ingest-file-requests-bulk".format(args.env)
    elif args.priority:
        spn_cdx_retry_sec = 45.0
        consume_group = "sandcrawler-{}-ingest-file-priority".format(args.env)
        consume_topic = "sandcrawler-{}.ingest-file-requests-priority".format(args.env)
    else:
        spn_cdx_retry_sec = 1.0
        consume_group = "sandcrawler-{}-ingest-file".format(args.env)
        consume_topic = "sandcrawler-{}.ingest-file-requests-daily".format(args.env)
    produce_topic = "sandcrawler-{}.ingest-file-results".format(args.env)
    grobid_topic = "sandcrawler-{}.grobid-output-pg".format(args.env)
    pdftext_topic = "sandcrawler-{}.pdf-text".format(args.env)
    thumbnail_topic = "sandcrawler-{}.pdf-thumbnail-180px-jpg".format(args.env)
    xmldoc_topic = "sandcrawler-{}.xml-doc".format(args.env)
    htmlteixml_topic = "sandcrawler-{}.html-teixml".format(args.env)
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
        sink=sink,
        grobid_sink=grobid_sink,
        thumbnail_sink=thumbnail_sink,
        pdftext_sink=pdftext_sink,
        xmldoc_sink=xmldoc_sink,
        htmlteixml_sink=htmlteixml_sink,
        # don't SPNv2 for --bulk or --skip-spn
        try_spn2=not (args.bulk or args.skip_spn),
        spn_cdx_retry_sec=spn_cdx_retry_sec,
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


def run_persist_crossref(args):
    batch_size = 200
    if args.parse_refs:
        batch_size = 10
    grobid_client = GrobidClient(host_url=args.grobid_host)
    consume_topic = "fatcat-{}.api-crossref".format(args.env)
    worker = PersistCrossrefWorker(
        db_url=args.db_url,
        grobid_client=grobid_client,
        parse_refs=args.parse_refs,
    )
    pusher = KafkaJsonPusher(
        worker=worker,
        kafka_hosts=args.kafka_hosts,
        consume_topic=consume_topic,
        group="persist-crossref",
        push_batches=True,
        # small batch size because doing GROBID processing
        batch_size=batch_size,
    )
    pusher.run()


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--kafka-hosts",
        default="localhost:9092",
        help="list of Kafka brokers (host/port) to use",
    )
    parser.add_argument(
        "--env", default="dev", help="Kafka topic namespace to use (eg, prod, qa, dev)"
    )
    parser.add_argument(
        "--kafka-group-suffix", default="", help="Kafka consumer group suffix (optional)"
    )
    parser.add_argument(
        "--grobid-host", default="https://grobid.qa.fatcat.wiki", help="GROBID API host/port"
    )
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
        default=os.environ.get("SANDCRAWLER_BLOB_SECRET_KEY")
        or os.environ.get("MINIO_SECRET_KEY"),
    )
    parser.add_argument(
        "--s3-bucket", help="S3 (seaweedfs) bucket to persist into", default="sandcrawler-dev"
    )
    subparsers = parser.add_subparsers()

    sub_grobid_extract = subparsers.add_parser(
        "grobid-extract",
        help="daemon that consumes CDX JSON objects from Kafka, uses GROBID to extract XML, pushes to Kafka",
    )
    sub_grobid_extract.set_defaults(func=run_grobid_extract)

    sub_pdf_extract = subparsers.add_parser(
        "pdf-extract",
        help="daemon that consumes CDX JSON objects from Kafka, extracts text and thumbnail, pushes to Kafka",
    )
    sub_pdf_extract.set_defaults(func=run_pdf_extract)

    sub_persist_grobid = subparsers.add_parser(
        "persist-grobid",
        help="daemon that consumes GROBID output from Kafka and pushes to S3 (seaweedfs) and postgres",
    )
    sub_persist_grobid.add_argument(
        "--s3-only",
        action="store_true",
        help="only upload TEI-XML to S3 (don't write to database)",
    )
    sub_persist_grobid.add_argument(
        "--db-only",
        action="store_true",
        help="only write status to database (don't upload TEI-XML to S3)",
    )
    sub_persist_grobid.set_defaults(func=run_persist_grobid)

    sub_persist_pdftext = subparsers.add_parser(
        "persist-pdftext",
        help="daemon that consumes pdftext output from Kafka and pushes to S3 (seaweedfs) and postgres",
    )
    sub_persist_pdftext.add_argument(
        "--s3-only",
        action="store_true",
        help="only upload TEI-XML to S3 (don't write to database)",
    )
    sub_persist_pdftext.add_argument(
        "--db-only",
        action="store_true",
        help="only write status to database (don't upload TEI-XML to S3)",
    )
    sub_persist_pdftext.set_defaults(func=run_persist_pdftext)

    sub_persist_thumbnail = subparsers.add_parser(
        "persist-thumbnail",
        help="daemon that consumes thumbnail output from Kafka and pushes to S3 (seaweedfs) and postgres",
    )
    sub_persist_thumbnail.set_defaults(func=run_persist_thumbnail)

    sub_persist_xml_doc = subparsers.add_parser(
        "persist-xml-doc",
        help="daemon that consumes xml-doc output from Kafka and pushes to S3 (seaweedfs) bucket",
    )
    sub_persist_xml_doc.set_defaults(func=run_persist_xml_doc)

    sub_persist_html_teixml = subparsers.add_parser(
        "persist-html-teixml",
        help="daemon that consumes html-teixml output from Kafka and pushes to S3 (seaweedfs) bucket",
    )
    sub_persist_html_teixml.set_defaults(func=run_persist_html_teixml)

    sub_persist_pdftrio = subparsers.add_parser(
        "persist-pdftrio",
        help="daemon that consumes pdftrio output from Kafka and pushes to postgres",
    )
    sub_persist_pdftrio.set_defaults(func=run_persist_pdftrio)

    sub_ingest_file = subparsers.add_parser(
        "ingest-file",
        help="daemon that consumes requests from Kafka, ingests, pushes results to Kafka",
    )
    sub_ingest_file.add_argument(
        "--bulk",
        action="store_true",
        help="consume from bulk kafka topic (eg, for ingest backfill)",
    )
    sub_ingest_file.add_argument(
        "--skip-spn",
        action="store_true",
        help="don't do SPN lookups",
    )
    sub_ingest_file.add_argument(
        "--priority",
        action="store_true",
        help="consume from priority kafka topic (eg, for SPN requests)",
    )
    sub_ingest_file.set_defaults(func=run_ingest_file)

    sub_persist_ingest_file = subparsers.add_parser(
        "persist-ingest-file",
        help="daemon that consumes ingest-file output from Kafka and pushes to postgres",
    )
    sub_persist_ingest_file.set_defaults(func=run_persist_ingest_file)

    sub_persist_crossref = subparsers.add_parser(
        "persist-crossref",
        help="daemon that persists crossref to postgres; also does GROBID ref transform",
    )
    sub_persist_crossref.add_argument(
        "--grobid-host", default="https://grobid.qa.fatcat.wiki", help="GROBID API host/port"
    )
    sub_persist_crossref.add_argument(
        "--parse-refs",
        action="store_true",
        help="use GROBID to parse any unstructured references (default is to not)",
    )
    sub_persist_crossref.set_defaults(func=run_persist_crossref)

    args = parser.parse_args()
    if not args.__dict__.get("func"):
        parser.print_help(file=sys.stderr)
        sys.exit(-1)

    # configure sentry *after* parsing args
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
