#!/usr/bin/env python3

import sys
import json
import argparse

from http.server import HTTPServer
from sandcrawler.ingest import IngestFileRequestHandler, IngestFileWorker


def run_single_ingest(args):
    request = dict(
        ingest_type=args.type,
        base_url=args.url,
        ext_ids=dict(doi=args.doi),
        fatcat=dict(release_ident=args.release_id),
    )
    if args.force_recrawl:
        request['force_recrawl'] = True
    ingester = IngestFileWorker(
        try_spn2=not args.no_spn2,
    )
    result = ingester.process(request)
    print(json.dumps(result, sort_keys=True))
    return result

def run_requests(args):
    # TODO: switch to using JsonLinePusher
    ingester = IngestFileWorker()
    for l in args.json_file:
        request = json.loads(l.strip())
        result = ingester.process(request)
        print(json.dumps(result, sort_keys=True))

def run_api(args):
    port = 8083
    print("Listening on localhost:{}".format(port))
    server = HTTPServer(('', port), IngestFileRequestHandler)
    server.serve_forever()

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    subparsers = parser.add_subparsers()

    sub_single= subparsers.add_parser('single',
        help="ingests a single file URL")
    sub_single.set_defaults(func=run_single_ingest)
    sub_single.add_argument('--release-id',
        help="(optional) existing release ident to match to")
    sub_single.add_argument('--doi',
        help="(optional) existing release DOI to match to")
    sub_single.add_argument('--force-recrawl',
        action='store_true',
        help="ignore GWB history and use SPNv2 to re-crawl")
    sub_single.add_argument('--no-spn2',
        action='store_true',
        help="don't use live web (SPNv2)")
    sub_single.add_argument('--type',
        default="pdf",
        help="type of ingest (pdf, html, etc)")
    sub_single.add_argument('url',
        help="URL of paper to fetch")

    sub_requests = subparsers.add_parser('requests',
        help="takes a series of ingest requests (JSON, per line) and runs each")
    sub_requests.set_defaults(func=run_requests)
    sub_requests.add_argument('json_file',
        help="JSON file (request per line) to import from (or stdin)",
        default=sys.stdin, type=argparse.FileType('r'))

    sub_api = subparsers.add_parser('api',
        help="starts a simple HTTP server that processes ingest requests")
    sub_api.set_defaults(func=run_api)
    sub_api.add_argument('--port',
        help="HTTP port to listen on",
        default=8033, type=int)

    args = parser.parse_args()
    if not args.__dict__.get("func"):
        parser.print_help(file=sys.stderr)
        sys.exit(-1)

    args.func(args)

if __name__ == '__main__':
    main()
