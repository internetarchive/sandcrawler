#!/usr/bin/env python3
"""
Transform an unpaywall dump (JSON) into ingest requests.
"""

import argparse
import json
import sys

import urlcanon


def canon(s):
    parsed = urlcanon.parse_url(s)
    return str(urlcanon.whatwg(parsed))


def transform_cnki(obj):

    requests = []
    assert obj['cnki_id']

    requests = []
    requests.append({
        'base_url': canon(obj['info_url']),
        'ingest_type': 'pdf',
        'link_source': 'cnki_covid19',
        'link_source_id': obj['cnki_id'],
        'ingest_request_source': 'scrape-covid19',
    })
    if 'read_url' in obj:
        requests.append({
            'base_url': canon(obj['read_url']),
            'ingest_type': 'pdf',  # actually HTML
            'link_source': 'cnki_covid19',
            'link_source_id': obj['cnki_id'],
            'ingest_request_source': 'scrape-covid19',
        })

    return requests


def transform_wanfang(obj):

    assert obj['wanfang_id']
    return [{
        'base_url': canon(obj['url']),
        'ingest_type': 'pdf',
        'link_source': 'wanfang_covid19',
        'link_source_id': obj['wanfang_id'],
        'ingest_request_source': 'scrape-covid19',
    }]


def run(args):
    for l in args.json_file:
        if not l.strip():
            continue
        row = json.loads(l)

        if 'wanfang_id' in row:
            requests = transform_wanfang(row) or []
        elif 'cnki_id' in row:
            requests = transform_cnki(row) or []
        else:
            continue
        for r in requests:
            print("{}".format(json.dumps(r, sort_keys=True)))


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('json_file',
                        help="COVID-19 metadata file to use",
                        type=argparse.FileType('r'))
    subparsers = parser.add_subparsers()

    args = parser.parse_args()

    run(args)


if __name__ == '__main__':
    main()
