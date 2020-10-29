
import sys
import json
import datetime
import argparse
from typing import List, Optional, Any

import trafilatura
import pydantic
from selectolax.parser import HTMLParser

from sandcrawler.ia import WaybackClient, CdxApiClient, ResourceResult
from sandcrawler.misc import gen_file_metadata
from sandcrawler.html_metadata import BiblioMetadata, html_extract_resources, html_extract_biblio, load_adblock_rules


def html_extract_fulltext_teixml(doc: bytes) -> dict:
    tei_xml = trafilatura.extract(doc,
        tei_output=True,
        include_comments=False,
        include_formatting=True,
    )
    if tei_xml:
        return dict(status="success", tei_xml=tei_xml)
    else:
        return dict(status="empty-xml")

class WebResource(pydantic.BaseModel):
    surt: str
    timestamp: datetime.datetime
    url: str
    sha1hex: str
    mimetype: str
    status_code: int
    size: Optional[int]
    sha256hex: Optional[str]
    resource_type: Optional[str]


def quick_fetch_html_resources(resources: List[dict], cdx_client: CdxApiClient, when: Optional[datetime.datetime]) -> List[WebResource]:
    """
    This is the lazy version that just does a CDX lookup for each resource.

    Takes a list instead of single record because we may want to circuit break
    on failure, and may introduce concurrency internal to this function.
    """

    full = []
    for resource in resources:
        cdx_row = cdx_client.lookup_best(resource['url'])
        if not cdx_row:
            raise Exception("CDX lookup failed")
        if cdx_row.url != resource['url']:
            pass
            #raise Exception(
            #    f"CDX lookup URL mismatch: {cdx_row.url} != {resource['url']}")
        full.append(WebResource(
            surt=cdx_row.surt,
            timestamp=cdx_row.datetime,
            url=cdx_row.url,
            sha1hex=cdx_row.sha1hex,
            mimetype=cdx_row.mimetype,
            status_code=cdx_row.status_code,
            size=None,
            sha256hex=None,
            resource_type=resource['type'],
        ))

    return full


def fetch_html_resources(resources: List[dict], wayback_client: WaybackClient, when: Optional[datetime.datetime]) -> List[WebResource]:
    """
    This is the full version which fetches each resource from wayback/petabox
    and calculates additional hashes.

    Could make this concurrent in the future, eg: https://realpython.com/python-concurrency/#threading-version
    """

    full = []
    for resource in resources:
        wayback_resp = wayback_client.lookup_resource(resource['url'])
        if not wayback_resp:
            raise Exception("wayback lookup failed")
        assert wayback_resp.status == 'success'
        if wayback_resp.cdx.url != resource['url']:
            pass
            #raise Exception(
            #    f"CDX lookup URL mismatch: {cdx_row.url} != {resource['url']}")
        file_meta = gen_file_metadata(wayback_resp.body)
        assert file_meta['sha1hex'] == wayback_resp.cdx.sha1hex
        full.append(WebResource(
            surt=wayback_resp.cdx.surt,
            timestamp=wayback_resp.cdx.datetime,
            url=wayback_resp.cdx.url,
            sha1hex=file_meta['sha1hex'],
            mimetype=file_meta['mimetype'],
            status_code=wayback_resp.cdx.status_code,
            size=file_meta['size_bytes'],
            sha256hex=file_meta['sha256hex'],
            resource_type=resource['type'],
        ))

    return full


def run_single(url: str, timestamp: Optional[str] = None, quick_mode: bool = False) -> None:

    adblock = load_adblock_rules()
    wayback_client = WaybackClient()

    html_resource = wayback_client.lookup_resource(url, "text/html")
    if html_resource.status != "success":
        print(json.dumps(html_resource, indent=2))
        return

    file_meta = gen_file_metadata(html_resource.body)
    # XXX:
    assert file_meta['mimetype'] == "text/html"

    html_doc = HTMLParser(html_resource.body)
    html_meta = html_extract_biblio(html_doc)
    html_fulltext = html_extract_fulltext_teixml(html_resource.body)
    raw_resources = html_extract_resources(html_resource.terminal_url, html_doc, adblock)

    # XXX:
    when = None

    full_resources: List[WebResource] = []
    if quick_mode:
        full_resources = quick_fetch_html_resources(raw_resources, wayback_client.cdx_client, when)
    else:
        full_resources = fetch_html_resources(raw_resources, wayback_client, when)

    output = dict(
        status="success",
        #html_resource=html_resource,
        file_meta=file_meta,
        html_fulltext=html_fulltext,
        # XXX:
        html_meta=html_meta and html_meta.dict(exclude_none=True, exclude={'release_date'}),
        resources=[r.dict(exclude_none=True, exclude={'timestamp'}) for r in full_resources],
    )

    print(json.dumps(output, indent=2))


def main() -> None:
    """
    Run this command like:

        python -m sandcrawler.html_ingest
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subparsers = parser.add_subparsers()

    sub = subparsers.add_parser(
        "single", help="tries to ingest a single URL, dumps result to stdout"
    )
    sub.set_defaults(func="run_single")
    sub.add_argument(
        "url",
        help="URL to fetch",
        type=str,
    )
    sub.add_argument(
        "--timestamp",
        help="timestamp for which to fetch document from wayback",
        type=str,
    )
    sub.add_argument(
        "--quick-mode",
        help="don't fetch resources, only do CDX lookup",
        action="store_true",
    )

    args = parser.parse_args()
    if not args.__dict__.get("func"):
        parser.print_help(file=sys.stderr)
        sys.exit(-1)

    if args.func == "run_single":
        run_single(args.url, args.timestamp, args.quick_mode)
    else:
        #func = getattr(wp, args.func)
        #func()
        raise NotImplementedError()

if __name__ == "__main__":
    main()
