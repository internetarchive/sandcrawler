#!/usr/bin/python3

"""
This script is intended to be used for backfill ingest of old crawls. It can
also be used as a fast path for getting freshly crawled content into fatcat if
the crawl was a hit and the arabesque JSON was exported conservatively.

Run like:

    ./arabesque2ingestrequest.py example_arabesque.json --link-source pmc --extid-type pmcid > ingest_requests.json

Can then run through requests using that tool, or dump into kafka queue.
"""

import sys
import json
import argparse


def run(args):
    for l in args.json_file:
        if not l.strip():
            continue
        row = json.loads(l)
        if not row['hit']:
            continue

        request = {
            'base_url': row['final_url'],
            'ingest_type': 'pdf',
            'link_source': args.link_source,
            'link_source_id': row['identifier'],
            'ingest_request_source': args.ingest_request_source,
            'ext_ids': {
                args.extid_type: row['identifier'],
            },
        }
        if args.release_stage:
            assert args.release_stage in ('published', 'submitted', 'accepted', 'draft', 'update')
            request['release_stage'] = args.release_stage

        print("{}".format(json.dumps(request, sort_keys=True)))

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--link-source',
        required=True,
        help="link_source to include in request")
    parser.add_argument('--extid-type',
        required=True,
        help="extid to encode identifier as")
    parser.add_argument('--ingest-request-source',
        default="arabesque",
        help="to include in request")
    parser.add_argument('--release-stage',
        default=None,
        help="to include in request")
    parser.add_argument('json_file',
        help="arabesque output file to use",
        type=argparse.FileType('r'))
    subparsers = parser.add_subparsers()

    args = parser.parse_args()

    run(args)

if __name__ == '__main__':
    main()
