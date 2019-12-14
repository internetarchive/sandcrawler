#!/usr/bin/env python3

import sys
import json
import argparse

from http.server import HTTPServer
from sandcrawler.ingest import IngestFileRequestHandler, IngestFileWorker


def run_single_ingest(args):
    request = dict(
        base_url=args.url,
        ext_ids=dict(doi=args.doi),
        fatcat=dict(release_ident=args.release_id),
    )
    ingester = IngestFileWorker()
    result = ingester.process(request)
    print(json.dumps(result))
    return result

def run_requests(args):
    # TODO: switch to using JsonLinePusher
    ingester = IngestFileWorker()
    for l in args.json_file:
        request = json.loads(l.strip())
        result = ingester.process(request)
        print(json.dumps(result))

def run_api(args):
    port = 8083
    print("Listening on localhost:{}".format(port))
    server = HTTPServer(('', port), IngestFileRequestHandler)
    server.serve_forever()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-host-url',
        default="http://localhost:9411/v0",
        help="fatcat API host/port to use")
    subparsers = parser.add_subparsers()

    sub_single= subparsers.add_parser('single')
    sub_single.set_defaults(func=run_single_ingest)
    sub_single.add_argument('--release-id',
        help="(optional) existing release ident to match to")
    sub_single.add_argument('--doi',
        help="(optional) existing release DOI to match to")
    sub_single.add_argument('url',
        help="URL of paper to fetch")

    sub_requests = subparsers.add_parser('requests')
    sub_requests.set_defaults(func=run_requests)
    sub_requests.add_argument('json_file',
        help="JSON file (request per line) to import from (or stdin)",
        default=sys.stdin, type=argparse.FileType('r'))

    sub_api = subparsers.add_parser('api')
    sub_api.set_defaults(func=run_api)
    sub_api.add_argument('--port',
        help="HTTP port to listen on",
        default=8033, type=int)

    args = parser.parse_args()
    if not args.__dict__.get("func"):
        sys.stderr.write("tell me what to do!\n")
        sys.exit(-1)

    args.func(args)

if __name__ == '__main__':
    main()
