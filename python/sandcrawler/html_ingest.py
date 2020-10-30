
import io
import sys
import gzip
import json
import datetime
import argparse
import xml.etree.ElementTree as ET
from typing import List, Optional, Any

import trafilatura
import pydantic
from selectolax.parser import HTMLParser

from sandcrawler.ia import WaybackClient, CdxApiClient, ResourceResult, cdx_to_dict
from sandcrawler.misc import gen_file_metadata, parse_cdx_datetime, datetime_to_cdx
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

def teixml_body_text(doc_xml: str) -> str:
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    tree = ET.fromstring(doc_xml)
    body = tree.find('.//tei:body', ns)
    if body:
        return " ".join(body.itertext())
    else:
        return ""

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

    class Config:
        json_encoders = {
            datetime.datetime: lambda dt: dt.isoformat()
        }

class IngestWebResult(pydantic.BaseModel):
    status: str
    hit: bool
    cdx: Optional[dict]
    terminal: Optional[Any] # TODO
    request: Optional[Any]  # TODO
    file_meta: Optional[dict]
    html_biblio: Optional[BiblioMetadata]
    html_scope: Optional[str]
    html_fulltext: Optional[dict]
    subresources: Optional[List[WebResource]]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime.datetime: lambda dt: dt.isoformat(),
        }


def fix_transfer_encoding(file_meta: dict, resource: ResourceResult) -> (dict, ResourceResult):
    if file_meta['mimetype'] == 'application/gzip' and resource.cdx and resource.cdx.mimetype != 'application/gzip':
        print("transfer encoding not stripped: {}".format(resource.cdx.mimetype), file=sys.stderr)
        inner_body = gzip.decompress(resource.body)
        inner_resource = ResourceResult(
            body=inner_body,
            # copy all other fields
            start_url=resource.start_url,
            hit=resource.hit,
            status=resource.status,
            terminal_url=resource.terminal_url,
            terminal_dt=resource.terminal_dt,
            terminal_status_code=resource.terminal_status_code,
            cdx=resource.cdx,
            revisit_cdx=resource.revisit_cdx,
        )
        inner_file_meta = gen_file_metadata(inner_resource.body)
        return (inner_file_meta, inner_resource)
    else:
        return (file_meta, resource)


def quick_fetch_html_resources(resources: List[dict], cdx_client: CdxApiClient, when: Optional[datetime.datetime]) -> List[WebResource]:
    """
    This is the lazy version that just does a CDX lookup for each resource.

    Takes a list instead of single record because we may want to circuit break
    on failure, and may introduce concurrency internal to this function.
    """

    full = []
    closest = when and datetime_to_cdx(when)
    for resource in resources:
        cdx_row = cdx_client.lookup_best(resource['url'], closest=closest)
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
    closest = when and datetime_to_cdx(when)
    for resource in resources:
        wayback_resp = wayback_client.lookup_resource(resource['url'], closest=closest)
        if not wayback_resp:
            raise Exception("wayback lookup failed")
        # XXX
        assert wayback_resp.status == 'success'
        file_meta = gen_file_metadata(wayback_resp.body)
        if file_meta['sha1hex'] != wayback_resp.cdx.sha1hex:
            raise Exception("wayback payload sha1hex mismatch")
        full.append(WebResource(
            surt=wayback_resp.cdx.surt,
            timestamp=parse_cdx_datetime(wayback_resp.cdx.datetime),
            url=wayback_resp.cdx.url,
            sha1hex=file_meta['sha1hex'],
            mimetype=file_meta['mimetype'],
            status_code=wayback_resp.cdx.status_code,
            size=file_meta['size_bytes'],
            sha256hex=file_meta['sha256hex'],
            resource_type=resource['type'],
        ))

    return full


def html_guess_scope(url: str, doc: HTMLParser, biblio: Optional[BiblioMetadata], tei_xml: Optional[str]) -> str:
    """
    This function tries to guess if an HTML document represents one of:

    - article-fulltext
    - article-abstract
    - article-sample
    - supplement
    - component
    - issue-fulltext
    - landingpage
    - paywall
    - loginwall
    - blockpage
    - errorpage
    - stub
    - unknown
    """

    # basic paywall and loginwall detection based on URL
    if url.endswith("/cookieAbsent"):
        return "blockpage"
    if "://page-one.live.cf.public.springer.com" in url:
        return "article-sample"

    if biblio and biblio.html_fulltext_url == url:
        return "article-fulltext"

    # fallback: guess based word count (arbitrary guesses here)
    if not tei_xml:
        return "unknown"
    body_txt = teixml_body_text(tei_xml)
    word_count = len(body_txt.split())
    #print(f"  body text word count: {word_count}", file=sys.stderr)
    if word_count < 20:
        return "stub"
    elif word_count > 800:
        return "article-fulltext"

    return "unknown"


def run_single(url: str, timestamp: Optional[str] = None, quick_mode: bool = False) -> IngestWebResult:

    adblock = load_adblock_rules()
    wayback_client = WaybackClient()

    html_resource = wayback_client.lookup_resource(url, "text/html", closest=timestamp)
    if html_resource.status != "success":
        return IngestWebResult(
            status=html_resource.status,
            hit=False,
            cdx=html_resource.cdx and cdx_to_dict(html_resource.cdx),
        )

    assert html_resource.terminal_status_code == 200

    file_meta = gen_file_metadata(html_resource.body)
    file_meta, html_resource = fix_transfer_encoding(file_meta, html_resource)

    if file_meta['mimetype'] not in ("text/html", "text/xml"):
        return IngestWebResult(
            status="wrong-mimetype",
            hit=False,
            cdx=html_resource.cdx and cdx_to_dict(html_resource.cdx),
            file_meta=file_meta,
        )

    html_doc = HTMLParser(html_resource.body)
    html_biblio = html_extract_biblio(html_doc)
    html_fulltext = html_extract_fulltext_teixml(html_resource.body)
    html_scope = html_guess_scope(url, html_doc, html_biblio, html_fulltext.get('tei_xml'))
    if html_scope not in ('article-fulltext', 'unknown'):
        return IngestWebResult(
            status="wrong-scope",
            hit=False,
            cdx=html_resource.cdx and cdx_to_dict(html_resource.cdx),
            file_meta=file_meta,
            html_biblio=html_biblio,
            html_scope=html_scope,
        )

    raw_resources = html_extract_resources(html_resource.terminal_url, html_doc, adblock)
    assert len(raw_resources) <= 200

    when = parse_cdx_datetime(html_resource.cdx.datetime)

    full_resources: List[WebResource] = []
    if quick_mode:
        full_resources = quick_fetch_html_resources(raw_resources, wayback_client.cdx_client, when)
    else:
        full_resources = fetch_html_resources(raw_resources, wayback_client, when)

    output = IngestWebResult(
        status="success",
        hit=True,
        cdx=html_resource.cdx and cdx_to_dict(html_resource.cdx),
        file_meta=file_meta,
        html_fulltext=html_fulltext,
        html_biblio=html_biblio,
        html_scope=html_scope,
        subresources=full_resources,
    )
    return output


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
        result = run_single(args.url, args.timestamp, args.quick_mode)
        print(result.json(indent=2, exclude_none=True))
    else:
        #func = getattr(wp, args.func)
        #func()
        raise NotImplementedError()

if __name__ == "__main__":
    main()
