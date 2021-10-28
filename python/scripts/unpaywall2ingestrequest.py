#!/usr/bin/env python3
"""
Transform an unpaywall dump (JSON) into ingest requests.
"""

import argparse
import json
import sys

import urlcanon

DOMAIN_BLOCKLIST = [
    # large OA publishers (we get via DOI)
    # large repos and aggregators (we crawl directly)
    "://arxiv.org/",
    "://europepmc.org/",
    "ncbi.nlm.nih.gov/",
    "semanticscholar.org/",
    "://doi.org/",
    "zenodo.org/",
    "figshare.com/",
    "://archive.org/",
    ".archive.org/",
]

RELEASE_STAGE_MAP = {
    "draftVersion": "draft",
    "submittedVersion": "submitted",
    "acceptedVersion": "accepted",
    "publishedVersion": "published",
    "updatedVersion": "updated",
}


def canon(s):
    parsed = urlcanon.parse_url(s)
    return str(urlcanon.whatwg(parsed))


def transform(obj):
    """
    Transforms from a single unpaywall object to zero or more ingest requests.
    Returns a list of dicts.
    """

    requests = []
    if not obj["doi"].startswith("10."):
        return requests
    if not obj["oa_locations"]:
        return requests

    for location in obj["oa_locations"]:
        if not location["url_for_pdf"]:
            continue
        skip = False
        for domain in DOMAIN_BLOCKLIST:
            if domain in location["url_for_pdf"]:
                skip = True
        if skip:
            continue
        try:
            base_url = canon(location["url_for_pdf"])
        except UnicodeEncodeError:
            continue

        request = {
            "base_url": base_url,
            "ingest_type": "pdf",
            "link_source": "unpaywall",
            "link_source_id": obj["doi"].lower(),
            "ingest_request_source": "unpaywall",
            "release_stage": RELEASE_STAGE_MAP.get(location["version"]),
            "rel": location["host_type"],
            "ext_ids": {
                "doi": obj["doi"].lower(),
            },
            "edit_extra": {},
        }
        if obj.get("oa_status"):
            request["edit_extra"]["oa_status"] = obj["oa_status"]
        if location.get("evidence"):
            request["edit_extra"]["evidence"] = location["evidence"]
        if location["pmh_id"]:
            request["ext_ids"]["pmh_id"] = location["pmh_id"]
        requests.append(request)

    return requests


def run(args):
    for l in args.json_file:
        if not l.strip():
            continue
        row = json.loads(l)

        requests = transform(row) or []
        for r in requests:
            print("{}".format(json.dumps(r, sort_keys=True)))


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "json_file", help="unpaywall dump file to use", type=argparse.FileType("r")
    )
    subparsers = parser.add_subparsers()

    args = parser.parse_args()

    run(args)


if __name__ == "__main__":
    main()
