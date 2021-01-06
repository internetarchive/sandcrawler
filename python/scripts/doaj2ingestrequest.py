#!/usr/bin/env python3

"""
Transform an DOAJ article dump (JSON) into ingest requests.

TODO: should we also attempt PDF ingest for HTML links? They seem to often be
landing pages. Or could have some pipeline that notices, eg, `citation_pdf_url`
in the HTML headers and adds an ingest request on that basis. Or even just run
the re-ingest in-process and publish a second result.
"""

import sys
import json
import argparse
import urlcanon
from typing import Optional, List

DOMAIN_BLOCKLIST = [
    # large OA publishers (we get via DOI)

    # large repos and aggregators (we crawl directly)
    "://arxiv.org/",
    "://europepmc.org/",
    "ncbi.nlm.nih.gov/",
    #"semanticscholar.org/",
    "://doi.org/",
    "zenodo.org/",
    "figshare.com/",
    "://archive.org/",
    ".archive.org/",

    # large publishers/platforms; may remove in the future
    #"://link.springer.com/",
    #"://dergipark.gov.tr/",
    #"frontiersin.org/",
    #"scielo",
]

# these default to PDF; note that we also do pdf ingests for HTML pages
CONTENT_TYPE_MAP = {
    "abstract": [],
    "doc": [],
    "": ["pdf"],

    "doi": ["pdf"],
    "url": ["pdf"],
    "fulltext": ["pdf"],
    "anySimpleType": ["pdf"],

    "application/pdf": ["pdf"],
    "html": ["html", "pdf"],
    "text/html": ["html", "pdf"],
    "xml": ["xml"],
}

def canon(s: str) -> str:
    parsed = urlcanon.parse_url(s)
    return str(urlcanon.whatwg(parsed))

def transform(obj: dict) -> List[dict]:
    """
    Transforms from a single DOAJ object to zero or more ingest requests.
    Returns a list of dicts.
    """

    doaj_id = obj['id'].lower()
    assert doaj_id

    bibjson = obj['bibjson']
    if not bibjson['link']:
        return []

    requests = []

    doi: Optional[str] = None
    for ident in (bibjson['identifier'] or []):
        if ident['type'].lower() == "doi" and ident.get('id') and ident['id'].startswith('10.'):
            doi = ident['id'].lower()

    for link in (bibjson['link'] or []):
        if link.get('type') != "fulltext" or not link.get('url'):
            continue
        ingest_types = CONTENT_TYPE_MAP.get((link.get('content_type') or '').lower())
        if not ingest_types:
            continue

        skip = False
        for domain in DOMAIN_BLOCKLIST:
            if domain in link['url'].lower():
                skip = True
        if skip:
            continue
        try:
            base_url = canon(link['url'].strip())
        except UnicodeEncodeError:
            continue

        if not base_url or len(base_url) > 1000:
            continue

        for ingest_type in ingest_types:
            request = {
                'base_url': base_url,
                'ingest_type': ingest_type,
                'link_source': 'doaj',
                'link_source_id': doaj_id,
                'ingest_request_source': 'doaj',
                'release_stage': 'published',
                'rel': 'publisher',
                'ext_ids': {
                    'doi': doi,
                    'doaj': doaj_id,
                },
                'edit_extra': {},
            }
            requests.append(request)

    return requests

def run(args) -> None:
    for l in args.json_file:
        if not l.strip():
            continue
        row = json.loads(l)

        requests = transform(row) or []
        for r in requests:
            print("{}".format(json.dumps(r, sort_keys=True)))

def main() -> None:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('json_file',
        help="DOAJ article dump file to use",
        type=argparse.FileType('r'))
    subparsers = parser.add_subparsers()

    args = parser.parse_args()

    run(args)

if __name__ == '__main__':
    main()
