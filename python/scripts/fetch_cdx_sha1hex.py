#!/usr/bin/env python3

"""
This is a helper script to take fatcat file entities with partial metadata (eg,
missing SHA256) and try to find one or more CDX record where the file may be
found in wayback.

This script uses the sandcrawler library and should be run like:

    head file_export.json | python -m scripts.fetch_cdx_sha1hex > results.json
"""

import base64
import json
import sys
from typing import List, Optional

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry  # pylint: disable=import-error

from sandcrawler.ia import CdxApiClient, cdx_to_dict


def requests_retry_session(
    retries: int = 10,
    backoff_factor: int = 3,
    status_forcelist: List[int] = [500, 502, 504],
    session: requests.Session = None,
) -> requests.Session:
    """
    From: https://www.peterbe.com/plog/best-practice-with-retries-with-requests
    """
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def b32_hex(s: str) -> str:
    """
    Converts a base32-encoded SHA-1 checksum into hex-encoded

    base32 checksums are used by, eg, heritrix and in wayback CDX files
    """
    s = s.strip().split()[0].lower()
    if s.startswith("sha1:"):
        s = s[5:]
    if len(s) != 32:
        if len(s) == 40:
            return s
        raise ValueError("not a base-32 encoded SHA-1 hash: {}".format(s))
    return base64.b16encode(base64.b32decode(s.upper())).lower().decode("utf-8")


SANDCRAWLER_POSTGREST_URL = "http://wbgrp-svc506.us.archive.org:3030"


def get_db_cdx(sha1hex: str, http_session) -> List[dict]:
    resp = http_session.get(
        SANDCRAWLER_POSTGREST_URL + "/cdx", params=dict(sha1hex="eq." + sha1hex)
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows or []


CDX_API_URL = "https://web.archive.org/cdx/search/cdx"


def get_api_cdx(url: str, sha1hex: str, cdx_api) -> Optional[dict]:

    params = {
        "url": url,
        "output": "json",
        "matchType": "exact",
        "limit": 20,
        # TODO: group-by digest/checksum?
        # can't filter status because might be warc/revisit
        # "filter": "statuscode:200",
    }
    rows = cdx_api._query_api(params)
    if not rows:
        return None
    for row in rows:
        if row.sha1hex == sha1hex:
            return row
    return None


def process_file(fe, session, cdx_api) -> dict:
    status = "unknown"

    # simple CDX db lookup first
    cdx_row_list = get_db_cdx(fe["sha1"], http_session=session)
    if cdx_row_list:
        return dict(
            file_entity=fe,
            cdx_rows=cdx_row_list,
            status="success-db",
        )

    original_urls = []
    for pair in fe["urls"]:
        u = pair["url"]
        if not "://web.archive.org/web/" in u:
            continue
        seg = u.split("/")
        assert seg[2] == "web.archive.org"
        assert seg[3] == "web"
        if not seg[4].isdigit():
            continue
        original_url = "/".join(seg[5:])
        original_urls.append(original_url)

    if len(original_urls) == 0:
        return dict(file_entity=fe, status="skip-no-urls")

    found_cdx_rows = []
    for url in list(set(original_urls)):

        cdx_record = None
        try:
            cdx_record = get_api_cdx(original_url, sha1hex=fe["sha1"], cdx_api=cdx_api)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                return dict(file_entity=fe, status="fail-cdx-403")
            else:
                raise
        if cdx_record and cdx_record.sha1hex == fe["sha1"]:
            found_cdx_rows.append(cdx_to_dict(cdx_record))

    if found_cdx_rows:
        return dict(
            file_entity=fe,
            cdx_rows=found_cdx_rows,
            status="success-api",
        )

    return dict(
        file_entity=fe,
        status="fail-not-found",
    )


def main():
    session = requests_retry_session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 fatcat.CdxFixupBot",
        }
    )
    cdx_api = CdxApiClient()
    for line in sys.stdin:
        if not line.strip():
            continue
        fe = json.loads(line)
        print(json.dumps(process_file(fe, session=session, cdx_api=cdx_api)))


if __name__ == "__main__":
    main()
