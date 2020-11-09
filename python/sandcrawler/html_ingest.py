
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

from sandcrawler.ia import WaybackClient, CdxApiClient, ResourceResult, cdx_to_dict, fix_transfer_encoding, NoCaptureError, WaybackContentError
from sandcrawler.misc import gen_file_metadata, parse_cdx_datetime, datetime_to_cdx, clean_url, url_fuzzy_equal
from sandcrawler.html_metadata import BiblioMetadata, html_extract_resources, html_extract_biblio, load_adblock_rules


TRAFILATURA_AGENT = f"trafilatura/{trafilatura.__version__}"

def html_extract_body_teixml(doc: bytes) -> dict:
    try:
        tei_xml = trafilatura.extract(doc,
            tei_output=True,
            include_comments=False,
            include_formatting=True,
        )
    except (ValueError, TypeError) as e:
        return dict(
            status="parse-error",
            error_msg=str(e)[:1000],
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
        if cdx_row.url != resource['url'] and not url_fuzzy_equal(cdx_row.url, resource['url']):
            print(f"  WARN: CDX fuzzy match: {cdx_row.url} != {resource['url']}", file=sys.stderr)
        if not cdx_row.status_code:
            # TODO: fall back to a full fetch?
            print(f"  WARN: skipping revisit record", file=sys.stderr)
            continue
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
        file_meta = gen_file_metadata(wayback_resp.body, allow_empty=True)
        if file_meta['sha1hex'] != wayback_resp.cdx.sha1hex:
            raise WaybackContentError("wayback payload sha1hex mismatch: {wayback_resp.cdx.url}")
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


def html_guess_platform(url: str, doc: HTMLParser, biblio: Optional[BiblioMetadata]) -> Optional[str]:

    generator: Optional[str] = None
    generator_elem = doc.css_first("meta[name='generator']")
    if generator_elem:
        generator = generator_elem.attrs['content']
    else:
        generator_elem = doc.css_first("a[id='developedBy']")
        if generator_elem:
            generator = generator_elem.text()
    if generator and "open journal systems 3" in generator.lower():
        return "ojs3"
    elif generator and "open journal systems" in generator.lower():
        return "ojs"
    elif generator and "plone" in generator.lower():
        return "plone"
    elif doc.css_first("body[id='pkp-common-openJournalSystems']"):
        return "ojs"
    else:
        try:
            if 'powered by <a target="blank" href="http://pkp.sfu.ca/ojs/">PKP OJS</a>' in doc.html:
                return "ojs"
            if 'Powered by <a target="_blank" href="http://arphahub.com">' in doc.html:
                return "arpha"
            if "<meta property='og:image' content='http://cms.galenos.com.tr' />" in doc.html:
                return "galenos"
        except UnicodeDecodeError:
            pass

    icon_elem = doc.css_first("link[type='image/x-icon']")
    if icon_elem and 'href' in icon_elem.attrs:
        if 'journalssystem.com' in icon_elem.attrs['href']:
            return "journalssystem.com"
        elif 'indexcopernicus.com' in icon_elem.attrs['href']:
            return "indexcopernicus"

    if 'scielo' in url:
        return "scielo"

    return None

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
    - blocked-paywall
    - blocked-login
    - blocked-captcha
    - blocked-cookie
    - errorpage
    - stub
    - other
    - unknown

    Unknown implies the page could be anything. "other" implies it is not
    fulltext or a landing page, but could be one of the other categories.
    """

    # basic paywall and loginwall detection based on URL
    if url.endswith("/cookieAbsent"):
        return "blocked-cookie"
    if "://page-one.live.cf.public.springer.com" in url:
        return "article-sample"

    if "scielo" in url:
        if "sci_abstract" in url:
            return "landingpage"
        if "sci_arttext" in url:
            return "article-fulltext"

    if "showcaptcha.asp" in url:
        return "blocked-captcha"

    platform = html_guess_platform(url, doc, biblio)

    if biblio:
        if biblio.html_fulltext_url:
            if url_fuzzy_equal(biblio.html_fulltext_url, url):
                return "article-fulltext"
            else:
                return "landingpage"

    # platform-specific detection
    if platform in ("ojs", "ojs3"):

        if biblio and biblio.title:
            if word_count and word_count > 1200:
                return "fulltext"
            else:
                return "landingpage"
        else:
            if "/article/view/" in url and word_count and word_count > 600:
                return "fulltext"
        return "other"
    elif platform == "journalssystem.com":
        if biblio and biblio.pdf_fulltext_url and word_count and word_count < 1000:
            return "landingpage"

    # more platform/publisher specific checks
    if "karger.com/Article/Abstract" in url:
        return "landingpage"
    if "dergipark.gov.tr" in url and not ("download/article-file" in url):
        return "other"

    try:
        if isinstance(doc.html, str) and "<center><h1>403 Forbidden</h1></center>" in doc.html:
            # cloudflare block pattern
            return "blocked-forbidden"
    except UnicodeDecodeError:
        pass

    print(f"  scope guessing: platform {platform} word count: {word_count}", file=sys.stderr)

    # fallback: guess based on word count (arbitrary guesses here)
    if word_count is not None:
        if word_count < 20:
            return "stub"
        elif word_count > 1200:
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
