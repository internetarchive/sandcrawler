
import io
import sys
import json
import datetime
import argparse
import xml.etree.ElementTree as ET
from typing import List, Optional, Any, Tuple

import trafilatura
import pydantic
from selectolax.parser import HTMLParser

from sandcrawler.ia import WaybackClient, CdxApiClient, ResourceResult, cdx_to_dict, fix_transfer_encoding, NoCaptureError
from sandcrawler.misc import gen_file_metadata, parse_cdx_datetime, datetime_to_cdx
from sandcrawler.html_metadata import BiblioMetadata, html_extract_resources, html_extract_biblio, load_adblock_rules


TRAFILATURA_AGENT = f"trafilatura/{trafilatura.__version__}"

def html_extract_body_teixml(doc: bytes) -> dict:
    tei_xml = trafilatura.extract(doc,
        tei_output=True,
        include_comments=False,
        include_formatting=True,
    )
    if tei_xml:
        body_txt = teixml_body_text(tei_xml)
        word_count = len(body_txt.split())
        return dict(status="success", agent=TRAFILATURA_AGENT, tei_xml=tei_xml, word_count=word_count)
    elif doc.startswith(b'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" 2012"http://www.w3.org/TR/html4/loose.dtd">'):
        # hack for firstmonday.org
        return html_extract_body_teixml(doc[106:])
    else:
        return dict(status="empty-xml", agent=TRAFILATURA_AGENT)

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
    error_message: Optional[str]
    cdx: Optional[dict]
    terminal: Optional[Any] # TODO
    request: Optional[Any]  # TODO
    file_meta: Optional[dict]
    html_biblio: Optional[BiblioMetadata]
    scope: Optional[str]
    html_body: Optional[dict]
    html_resources: Optional[List[WebResource]]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime.datetime: lambda dt: dt.isoformat(),
        }

class HtmlMetaRow(pydantic.BaseModel):
    sha1hex: str
    status: str
    scope: Optional[str]
    has_teixml: bool
    has_thumbnail: bool
    word_count: Optional[int]
    biblio: Optional[dict]
    resources: Optional[List[dict]]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime.datetime: lambda dt: dt.isoformat(),
        }

    def to_sql_tuple(self) -> Tuple:
        """
        This is for the html_meta SQL table.
        """
        return (
            self.sha1hex,
            datetime.datetime.now(), # updated
            self.status,
            self.scope,
            self.has_teixml,
            self.has_thumbnail,
            self.word_count,
            (self.biblio or None) and json.dumps(self.biblio, sort_keys=True),
            (self.resources or None) and json.dumps(self.resources, sort_keys=True),
        )


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
            raise NoCaptureError(f"HTML sub-resource not found: {resource['url']}")
        if cdx_row.url != resource['url']:
            print(f"  WARN: CDX fuzzy match: {cdx_row.url} != {resource['url']}", file=sys.stderr)
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
        if not wayback_resp or wayback_resp.status != 'success':
            raise NoCaptureError(f"HTML sub-resource not found: {resource['url']}")
        file_meta = gen_file_metadata(wayback_resp.body)
        if file_meta['sha1hex'] != wayback_resp.cdx.sha1hex:
            raise WaybackError("wayback payload sha1hex mismatch: {wayback_resp.cdx.url}")
        full.append(WebResource(
            surt=wayback_resp.cdx.surt,
            timestamp=parse_cdx_datetime(wayback_resp.cdx.datetime),
            url=wayback_resp.cdx.url,
            sha1hex=file_meta['sha1hex'],
            mimetype=file_meta['mimetype'],
            status_code=wayback_resp.cdx.status_code or wayback_resp.revisit_cdx.status_code,
            size=file_meta['size_bytes'],
            sha256hex=file_meta['sha256hex'],
            resource_type=resource['type'],
        ))

    return full


def html_guess_scope(url: str, doc: HTMLParser, biblio: Optional[BiblioMetadata], word_count: Optional[int]) -> str:
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

    if "scielo" in url:
        if "sci_abstract" in url:
            return "landingpage"
        if "sci_arttext" in url:
            return "article-fulltext"

    if biblio and biblio.html_fulltext_url == url:
        return "article-fulltext"

    # fallback: guess based word count (arbitrary guesses here)
    if word_count == None:
        return "unknown"
    #print(f"  body text word count: {word_count}", file=sys.stderr)
    assert word_count is not None
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
    html_biblio = html_extract_biblio(url, html_doc)
    html_body = html_extract_body_teixml(html_resource.body)
    html_scope = html_guess_scope(url, html_doc, html_biblio, html_body.get('word_count'))
    if html_scope not in ('article-fulltext', 'unknown'):
        return IngestWebResult(
            status="wrong-scope",
            hit=False,
            cdx=html_resource.cdx and cdx_to_dict(html_resource.cdx),
            file_meta=file_meta,
            html_biblio=html_biblio,
            scope=html_scope,
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
        html_body=html_body,
        html_biblio=html_biblio,
        scope=html_scope,
        html_resources=full_resources,
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
