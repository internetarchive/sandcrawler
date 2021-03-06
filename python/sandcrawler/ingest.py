
import sys
import json
import gzip
import time
import base64
import xml.etree.ElementTree
from collections import namedtuple
from typing import Optional, Tuple, Any, Dict, List
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from selectolax.parser import HTMLParser

from sandcrawler.ia import SavePageNowClient, CdxApiClient, WaybackClient, WaybackError, WaybackContentError, SavePageNowError, CdxApiError, PetaboxError, cdx_to_dict, ResourceResult, fix_transfer_encoding, NoCaptureError
from sandcrawler.grobid import GrobidClient
from sandcrawler.pdfextract import process_pdf, PdfExtractResult
from sandcrawler.misc import gen_file_metadata, clean_url, parse_cdx_datetime
from sandcrawler.html import extract_fulltext_url
from sandcrawler.html_ingest import fetch_html_resources, \
    quick_fetch_html_resources, html_guess_scope, html_extract_body_teixml, \
    WebResource, html_guess_platform
from sandcrawler.html_metadata import BiblioMetadata, html_extract_resources, html_extract_biblio, load_adblock_rules
from sandcrawler.workers import SandcrawlerWorker
from sandcrawler.db import SandcrawlerPostgrestClient
from sandcrawler.xml import xml_reserialize


class IngestFileWorker(SandcrawlerWorker):
    """
    High level flow is to look in history first, then go to live web if
    resource not found. Following redirects is treated as "fetching a
    resource". Current version fetches a single resource; if it isn't a hit
    but is an HTML 200, treats it as a landing page, tries to extract
    fulltext link, then fetches that resource.

        process(request, key=None) -> response
            Does all the things!

    Check existing processing (short circuit):

        check_existing_ingest(base_url) -> ingest_file_result or none
        process_existing(result) -> response
            try fetching all the rows we want. if any don't exist, fetch the resource itself and call process_hit()

    Fetch resource:

        find_resource(url) -> ResourceResult

    Process resource:

        process_hit(ResourceResult) -> response
        process_grobid(ResourceResult)
    """

    def __init__(self, sink=None, **kwargs):
        super().__init__()

        self.sink = sink
        self.wayback_client = kwargs.get('wayback_client')
        if not self.wayback_client:
            self.wayback_client = WaybackClient()
        self.spn_client = kwargs.get('spn_client')
        if not self.spn_client:
            self.spn_client = SavePageNowClient()
        self.grobid_client = kwargs.get('grobid_client')
        if not self.grobid_client:
            self.grobid_client = GrobidClient()
        self.pgrest_client = kwargs.get('pgrest_client')
        if not self.pgrest_client:
            self.pgrest_client = SandcrawlerPostgrestClient()
        self.grobid_sink = kwargs.get('grobid_sink')
        self.thumbnail_sink = kwargs.get('thumbnail_sink')
        self.pdftext_sink = kwargs.get('pdftext_sink')
        self.xmldoc_sink = kwargs.get('xmldoc_sink')
        self.htmlteixml_sink = kwargs.get('htmlteixml_sink')
        self.max_hops = 6

        self.try_existing_ingest = kwargs.get('try_existing_ingest', False)
        self.try_existing_grobid = kwargs.get('try_existing_grobid', True)
        self.try_existing_pdfextract = kwargs.get('try_existing_pdfextract', True)
        self.try_wayback = kwargs.get('try_wayback', True)
        self.try_spn2 = kwargs.get('try_spn2', True)
        self.html_quick_mode = kwargs.get('html_quick_mode', False)
        self.adblock_rules = load_adblock_rules()
        self.max_html_resources = 200

        self.base_url_blocklist = [
            # robot blocking
            "://hkvalidate.perfdrive.com/",

            # temporary, until we implement specific fetch and 'petabox' output
            "://archive.org/",
            "://www.archive.org/",
            "://web.archive.org/web/",
            "://openlibrary.org/",
            "://www.openlibrary.org/",
            "://fatcat.wiki/",

            # Domain squats
            "://bartandjones.com",
            "://ijretm.com",
            "://ijrcemas.com",
            "://jist.net.in",
            "://croisements-revue.org",

            # all stubs/previews, not full papers
            "://page-one.live.cf.public.springer.com",

            # large datasets-only (no PDF expected)
            "plutof.ut.ee/",
            "www.gbif.org/",
            "doi.pangaea.de/",
            "www.plate-archive.org/",
            "://doi.org/10.25642/ipk/gbis/",
            "://apex.ipk-gatersleben.de/",

            # Historical non-paper content:
            "dhz.uni-passau.de/",   # newspapers
            "digital.ucd.ie/",      # ireland national historical

            # DOI prefixes
            "://doi.org/10.2307/",  # JSTOR; slow and many redirects
        ]

        self.wall_blocklist = [
            # loginwall
            "://profile.thieme.de/HTML/sso/ejournals/login.htm",
            "://login.bepress.com/"
            "?SAMLRequest="
        ]

        # these are special-case web domains for which we want SPN2 to not run
        # a headless browser (brozzler), but instead simply run wget.
        # the motivation could be to work around browser issues, or in the
        # future possibly to increase download efficiency (wget/fetch being
        # faster than browser fetch)
        self.spn2_simple_get_domains = [
            # direct PDF links
            "://arxiv.org/pdf/",
            "://europepmc.org/backend/ptpmcrender.fcgi",
            "://pdfs.semanticscholar.org/",
            "://res.mdpi.com/",

            # platform sites
            "://zenodo.org/",
            "://figshare.org/",
            "://springernature.figshare.com/",

            # popular simple cloud storage or direct links
            "://s3-eu-west-1.amazonaws.com/",
        ]


    def check_existing_ingest(self, ingest_type: str, base_url: str) -> Optional[dict]:
        """
        Check in sandcrawler-db (postgres) to see if we have already ingested
        this URL (ingest file result table).

        Returns existing row *if* found *and* we should use it, otherwise None.

        Looks at existing ingest results and makes a decision based on, eg,
        status and timestamp.
        """
        if not self.try_existing_ingest:
            return None
        existing = self.pgrest_client.get_ingest_file_result(ingest_type, base_url)
        # TODO: filter on more flags?
        if existing and existing['hit'] == True:
            return existing
        else:
            return None

    def find_resource(self, url, best_mimetype=None, force_recrawl=False) -> Optional[ResourceResult]:
        """
        Looks in wayback for a resource starting at the URL, following any
        redirects. If a hit isn't found, try crawling with SPN.
        """
        via = "none"
        resource = None

        if url.startswith("http://web.archive.org/web/") or url.startswith("https://web.archive.org/web/"):
            raise NotImplementedError("handling direct wayback links not supported yet")

        if url.startswith("http://archive.org/") or url.startswith("https://archive.org/"):
            raise NotImplementedError("fetching from archive.org not implemented yet")

        if self.try_wayback and not force_recrawl:
            via = "wayback"
            resource = self.wayback_client.lookup_resource(url, best_mimetype)

        # check for "soft 404" conditions, where we should retry with live SPNv2
        soft404 = False
        # NOTE: these are often not working with SPNv2 either, so disabling. If
        # we really want to try again, should do force-recrawl
        #if resource and resource.hit and resource.terminal_url.endswith('/cookieAbsent'):
        #    soft404 = True

        old_failure = False
        if resource and not resource.hit and resource.terminal_dt and resource.terminal_dt < '20190000000000':
            old_failure = True

        if self.try_spn2 and (resource == None or (resource and resource.status == 'no-capture') or soft404 or old_failure):
            via = "spn2"
            force_simple_get = 0
            for domain in self.spn2_simple_get_domains:
                if domain in url:
                    force_simple_get = 1
                    break
            resource = self.spn_client.crawl_resource(url, self.wayback_client, force_simple_get=force_simple_get)
        print("[FETCH {:>6}] {}  {}".format(
                via,
                (resource and resource.status),
                (resource and resource.terminal_url) or url),
            file=sys.stderr)
        return resource

    def process_existing(self, request: dict, result_row: dict) -> dict:
        """
        If we have an existing ingest file result, do any database fetches or
        additional processing necessary to return a result.
        """
        raise NotImplementedError("process_existing() not tested or safe yet")
        assert result_row['hit']
        existing_file_meta = self.pgrest_client.get_grobid(result_row['terminal_sha1hex'])
        existing_grobid = self.pgrest_client.get_grobid(result_row['terminal_sha1hex'])
        existing_cdx = self.pgrest_client.get_cdx(result_row['terminal_url'], result_row['terminal_dt'])
        if not (existing_file_meta and existing_grobid and existing_cdx):
            raise NotImplementedError("partially-exsiting records not implemented yet")
        result = {
            'hit': result_row['hit'],
            'status': "existing",
            'request': request,
            'grobid': existing_grobid,
            'file_meta': existing_file_meta,
            'cdx': existing_cdx,
            'terminal': {
                'terminal_url': result_row['terminal_url'],
                'terminal_dt': result_row['terminal_dt'],
                'terminal_status_code': result_row['terminal_status_code'],
                'terminal_sha1hex': result_row['terminal_sha1hex'],
            },
        }
        return result

    def process_hit(self, ingest_type: str, resource: ResourceResult, file_meta: dict) -> dict:
        """
        Run all the necessary processing for a new/fresh ingest hit.
        """
        if ingest_type == "pdf":
            return {
                'grobid': self.process_grobid(resource, file_meta),
                'pdf_meta': self.process_pdfextract(resource, file_meta),
            }
        elif ingest_type == "xml":
            return {
                'xml_meta': self.process_xml(resource, file_meta),
            }
        elif ingest_type == "html":
            html_info = self.process_html(resource, file_meta)
            # if there is no html_biblio, don't clobber anything possibly extracted earlier
            if 'html_biblio' in html_info and not html_info['html_biblio']:
                html_info.pop('html_biblio')
            return html_info
        else:
            raise NotImplementedError(f"process {ingest_type} hit")

    def process_grobid(self, resource: ResourceResult, file_meta: dict) -> dict:
        """
        Submits to resource body to GROBID for processing.

        TODO: By default checks sandcrawler-db for an existing row first, then
        decide if we should re-process
        """
        if self.try_existing_grobid:
            existing = self.pgrest_client.get_grobid(file_meta['sha1hex'])
            if existing:
                print("found existing GROBID result", file=sys.stderr)
                return existing

        # Need to actually processes
        result = self.grobid_client.process_fulltext(resource.body)
        if self.grobid_sink:
            # extra fields for GROBID kafka messages
            result['file_meta'] = file_meta
            result['key'] = result['file_meta']['sha1hex']
            self.grobid_sink.push_record(result.copy())
        if result['status'] == "success":
            metadata = self.grobid_client.metadata(result)
            if metadata:
                result['metadata'] = self.grobid_client.metadata(result)
                result['fatcat_release'] = result['metadata'].pop('fatcat_release', None)
                result['grobid_version'] = result['metadata'].pop('grobid_version', None)
        result.pop('tei_xml', None)
        result.pop('file_meta', None)
        result.pop('key', None)
        return result

    def process_pdfextract(self, resource: ResourceResult, file_meta: dict) -> dict:
        """
        Extracts thumbnail and pdf_meta info from PDF.

        By default checks sandcrawler-db for an existing row first, then decide
        if we should re-process.

        TODO: difference between Kafka schema and SQL/postgrest schema
        """
        if self.try_existing_pdfextract:
            existing = self.pgrest_client.get_pdf_meta(file_meta['sha1hex'])
            if existing:
                print("found existing pdf_meta result", file=sys.stderr)
                result = PdfExtractResult.from_pdf_meta_dict(existing)
                return result.to_pdftext_dict()

        # Need to actually processes
        result = process_pdf(resource.body)
        assert result.file_meta['sha1hex'] == file_meta['sha1hex']
        if self.thumbnail_sink and result.page0_thumbnail is not None:
            self.thumbnail_sink.push_record(result.page0_thumbnail, key=result.sha1hex)
        if self.pdftext_sink:
            self.pdftext_sink.push_record(result.to_pdftext_dict(), key=result.sha1hex)
        result.page0_thumbnail = None
        result.text = None
        result.file_meta = None
        return result.to_pdftext_dict()

    def process_xml(self, resource: ResourceResult, file_meta: dict) -> dict:
        """
        Simply publishes to Kafka topic.

        In the future, could extract other metadata here (like body word
        count), or attempting to fetch sub-resources.
        """
        if self.xmldoc_sink and file_meta['mimetype'] == "application/jats+xml":
            try:
                jats_xml = xml_reserialize(resource.body)
            except xml.etree.ElementTree.ParseError:
                return dict(status="xml-parse-error")
            msg = dict(
                sha1hex=file_meta["sha1hex"],
                status="success",
                jats_xml=jats_xml,
            )
            self.xmldoc_sink.push_record(msg, key=file_meta['sha1hex'])
        return dict(status="success")

    def process_html(self, resource: ResourceResult, file_meta: dict) -> dict:

        assert resource.body
        try:
            html_doc = HTMLParser(resource.body)
        except ValueError as ve:
            return dict(
                status="html-selectolax-error",
            )
        html_biblio = html_extract_biblio(resource.terminal_url, html_doc)
        assert html_biblio
        html_body = html_extract_body_teixml(resource.body)
        html_platform = html_guess_platform(resource.terminal_url, html_doc, html_biblio)
        html_scope = html_guess_scope(resource.terminal_url, html_doc, html_biblio, html_body.get('word_count'))
        html_biblio_dict = json.loads(html_biblio.json(exclude_none=True))

        if html_scope in ('blocked-captcha','blocked-cookie','blocked-forbidden'):
            return dict(
                status=html_scope,
                html_biblio=html_biblio_dict,
                scope=html_scope,
                platform=html_platform,
            )
        elif html_scope == 'unknown':
            html_body.pop("tei_xml", None)
            return dict(
                status="unknown-scope",
                html_biblio=html_biblio_dict,
                scope=html_scope,
                platform=html_platform,
                html_body=html_body,
            )
        elif html_scope not in ('article-fulltext',):
            html_body.pop("tei_xml", None)
            return dict(
                status="wrong-scope",
                html_biblio=html_biblio_dict,
                scope=html_scope,
                platform=html_platform,
                html_body=html_body,
            )

        raw_resources = html_extract_resources(resource.terminal_url, html_doc, self.adblock_rules)
        if len(raw_resources) > self.max_html_resources:
            html_body.pop("tei_xml", None)
            return dict(
                status="too-many-resources",
                html_biblio=html_biblio_dict,
                scope=html_scope,
                platform=html_platform,
                html_body=html_body,
            )

        if self.htmlteixml_sink and html_body['status'] == "success":
            self.htmlteixml_sink.push_record(html_body, key=file_meta['sha1hex'])

        html_body.pop("tei_xml", None)

        partial_result = dict(
            html_biblio=html_biblio_dict,
            scope=html_scope,
            platform=html_platform,
            html_body=html_body,
        )

        when = parse_cdx_datetime(resource.cdx.datetime)
        full_resources: List[WebResource] = []

        try:
            if self.html_quick_mode:
                print("  WARN: running quick CDX-only fetches", file=sys.stderr)
                full_resources = quick_fetch_html_resources(raw_resources, self.wayback_client.cdx_client, when)
            else:
                full_resources = fetch_html_resources(raw_resources, self.wayback_client, when)
        except PetaboxError as e:
            partial_result['status'] = 'petabox-error'
            partial_result['error_message'] = str(e)[:1600]
            return partial_result
        except CdxApiError as e:
            partial_result['status'] = 'cdx-error'
            partial_result['error_message'] = str(e)[:1600]
            return partial_result
        except WaybackError as e:
            partial_result['status'] = 'wayback-error'
            partial_result['error_message'] = str(e)[:1600]
            return partial_result
        except WaybackContentError as e:
            partial_result['status'] = 'wayback-content-error'
            partial_result['error_message'] = str(e)[:1600]
            return partial_result
        except NoCaptureError as e:
            partial_result['status'] = 'html-resource-no-capture'
            partial_result['error_message'] = str(e)[:1600]
            return partial_result

        return dict(
            html_body=html_body,
            html_biblio=html_biblio_dict,
            scope=html_scope,
            platform=html_platform,
            html_resources=[json.loads(r.json(exclude_none=True)) for r in full_resources],
        )

    def timeout_response(self, task: dict) -> dict:
        print("[TIMEOUT]", file=sys.stderr)
        return dict(
            request=task,
            hit=False,
            status="timeout",
            error_message="ingest worker internal timeout",
        )

    def want(self, request: dict) -> bool:
        if not request.get('ingest_type') in ('file', 'pdf', 'xml', 'html'):
            return False
        return True

    def process(self, request: dict, key: Any = None) -> dict:

        # old backwards compatibility
        if request.get('ingest_type') == 'file':
            request['ingest_type'] = 'pdf'

        ingest_type = request.get('ingest_type')
        if ingest_type not in ("pdf", "xml", "html"):
            raise NotImplementedError(f"can't handle ingest_type={ingest_type}")

        # parse/clean URL
        # note that we pass through the original/raw URL, and that is what gets
        # persisted in database table
        base_url = clean_url(request['base_url'])

        force_recrawl = bool(request.get('force_recrawl', False))

        for block in self.base_url_blocklist:
            if block in base_url:
                print("[SKIP {:>6}] {}".format(ingest_type, base_url), file=sys.stderr)
                return dict(request=request, hit=False, status="skip-url-blocklist")

        print("[INGEST {:>6}] {}".format(ingest_type, base_url), file=sys.stderr)

        best_mimetype = None
        if ingest_type == "pdf":
            best_mimetype = "application/pdf"
        elif ingest_type == "xml":
            best_mimetype = "text/xml"
        elif ingest_type == "html":
            best_mimetype = "text/html"

        existing = self.check_existing_ingest(ingest_type, base_url)
        if existing:
            return self.process_existing(request, existing)

        result: Dict[str, Any] = dict(request=request, hit=False)

        next_url = base_url
        hops = [base_url]

        while len(hops) <= self.max_hops:

            result['hops'] = hops

            # check against blocklist again on each hop
            for block in self.base_url_blocklist:
                if block in next_url:
                    result['status'] = "skip-url-blocklist"
                    return result

            # check against known loginwall URLs
            for block in self.wall_blocklist:
                if block in next_url:
                    result['status'] = "skip-wall"
                    return result

            # check for popular cookie blocking URL patterns. On successful SPN
            # crawls, shouldn't see these redirect URLs
            if '/cookieAbsent' in next_url or 'cookieSet=1' in next_url:
                result['status'] = 'blocked-cookie'
                return result

            try:
                resource = self.find_resource(next_url, best_mimetype, force_recrawl=force_recrawl)
            except SavePageNowError as e:
                result['status'] = 'spn2-error'
                result['error_message'] = str(e)[:1600]
                return result
            except PetaboxError as e:
                result['status'] = 'petabox-error'
                result['error_message'] = str(e)[:1600]
                return result
            except CdxApiError as e:
                result['status'] = 'cdx-error'
                result['error_message'] = str(e)[:1600]
                # add a sleep in cdx-error path as a slow-down
                time.sleep(2.0)
                return result
            except WaybackError as e:
                result['status'] = 'wayback-error'
                result['error_message'] = str(e)[:1600]
                return result
            except WaybackContentError as e:
                result['status'] = 'wayback-content-error'
                result['error_message'] = str(e)[:1600]
                return result
            except NotImplementedError as e:
                result['status'] = 'not-implemented'
                result['error_message'] = str(e)[:1600]
                return result

            assert resource

            if resource.terminal_url:
                result['terminal'] = {
                    "terminal_url": resource.terminal_url,
                    "terminal_dt": resource.terminal_dt,
                    "terminal_status_code": resource.terminal_status_code,
                }
                if resource.terminal_url not in result['hops']:
                    result['hops'].append(resource.terminal_url)

            if not resource.hit:
                result['status'] = resource.status
                return result

            if resource.terminal_url and ('/cookieAbsent' in next_url or 'cookieSet=1' in resource.terminal_url):
                result['status'] = 'blocked-cookie'
                return result

            if not resource.body:
                result['status'] = 'null-body'
                return result

            file_meta = gen_file_metadata(resource.body)
            try:
                file_meta, resource = fix_transfer_encoding(file_meta, resource)
            except Exception as e:
                result['status'] = 'bad-gzip-encoding'
                result['error_message'] = str(e)
                return result

            if not resource.body or file_meta['size_bytes'] == 0:
                result['status'] = 'null-body'
                return result

            # here we split based on ingest type to try and extract a next hop
            html_ish_resource = bool(
                "html" in file_meta['mimetype']
                or "xhtml" in file_meta['mimetype'] # matches "application/xhtml+xml"
                or "application/xml" in file_meta['mimetype']
                or "text/xml" in file_meta['mimetype']
            )
            html_biblio = None
            html_doc = None
            if html_ish_resource and resource.body:
                try:
                    html_doc = HTMLParser(resource.body)
                    html_biblio = html_extract_biblio(resource.terminal_url, html_doc)
                    if html_biblio:
                        if not 'html_biblio' in result or html_biblio.title:
                            result['html_biblio'] = json.loads(html_biblio.json(exclude_none=True))
                            #print(f"  setting html_biblio: {result['html_biblio']}", file=sys.stderr)
                except ValueError:
                    pass

            if ingest_type == "pdf" and html_ish_resource:

                # the new style of URL extraction (already computed)
                if html_biblio and html_biblio.pdf_fulltext_url:
                    fulltext_url = dict(
                        pdf_url=html_biblio.pdf_fulltext_url,
                        technique="html_biblio",
                    )
                else:
                    fulltext_url = extract_fulltext_url(resource.terminal_url, resource.body)

                result['extract_next_hop'] = fulltext_url
                if not fulltext_url:
                    result['status'] = 'no-pdf-link'
                    return result
                next_url = fulltext_url.get('pdf_url') or fulltext_url.get('next_url') or ""
                assert next_url
                next_url = clean_url(next_url)
                print("[PARSE  {:>6}] {}  {}".format(
                        ingest_type,
                        fulltext_url.get('technique'),
                        next_url,
                    ),
                    file=sys.stderr)
                if next_url in hops:
                    result['status'] = 'link-loop'
                    result['error_message'] = "repeated: {}".format(next_url)
                    return result
                hops.append(next_url)
                continue
            elif ingest_type == "xml" and html_ish_resource:
                if html_biblio and html_biblio.xml_fulltext_url:
                    next_url = html_biblio.xml_fulltext_url
                    technique = "html_biblio"
                    print("[PARSE  {:>6}] {}  {}".format(
                            ingest_type,
                            technique,
                            next_url,
                        ),
                        file=sys.stderr)
                    if next_url in hops:
                        result['status'] = 'link-loop'
                        result['error_message'] = "repeated: {}".format(next_url)
                        return result
                    hops.append(next_url)
                    continue
            elif ingest_type == "html" and html_ish_resource:
                if html_biblio and html_biblio.html_fulltext_url:
                    next_url = html_biblio.html_fulltext_url
                    technique = "html_biblio"
                    if next_url in hops:
                        # for HTML ingest, we don't count this as a link-loop
                        break
                    print("[PARSE  {:>6}] {}  {}".format(
                            ingest_type,
                            technique,
                            next_url,
                        ),
                        file=sys.stderr)
                    hops.append(next_url)
                    continue

            # default is to NOT keep hopping
            break

        if len(hops) >= self.max_hops:
            result['status'] = "max-hops-exceeded"
            return result

        # fetch must be a hit if we got this far (though not necessarily an ingest hit!)
        assert resource
        assert resource.hit == True
        assert resource.terminal_status_code in (200, 226)

        if resource.terminal_url:
            result['terminal'] = {
                "terminal_url": resource.terminal_url,
                "terminal_dt": resource.terminal_dt,
                "terminal_status_code": resource.terminal_status_code,
                "terminal_sha1hex": file_meta['sha1hex'],
            }

        result['file_meta'] = file_meta
        result['cdx'] = cdx_to_dict(resource.cdx)
        if resource.revisit_cdx:
            result['revisit_cdx'] = cdx_to_dict(resource.revisit_cdx)

        if ingest_type == "pdf":
            if file_meta['mimetype'] != "application/pdf":
                result['status'] = "wrong-mimetype"  # formerly: "other-mimetype"
                return result
        elif ingest_type == "xml":
            if file_meta['mimetype'] not in ("application/xml", "text/xml", "application/jats+xml"):
                result['status'] = "wrong-mimetype"
                return result
        elif ingest_type == "html":
            if file_meta['mimetype'] not in ("text/html", "application/xhtml+xml"):
                result['status'] = "wrong-mimetype"
                return result
        else:
            raise NotImplementedError()

        info = self.process_hit(ingest_type, resource, file_meta)
        result.update(info)

        # check if processing turned up an error
        if info.get('status') not in ('success', None):
            result['status'] = info['status']
            return result

        result['status'] = "success"
        result['hit'] = True
        if ingest_type == "pdf":
            print("[SUCCESS {:>5}] sha1:{} grobid:{} pdfextract:{}".format(
                    ingest_type,
                    result.get('file_meta', {}).get('sha1hex'),
                    result.get('grobid', {}).get('status_code'),
                    result.get('pdf_meta', {}).get('status'),
                ),
                file=sys.stderr)
        else:
            print("[SUCCESS {:>5}] sha1:{}".format(
                    ingest_type,
                    result.get('file_meta', {}).get('sha1hex'),
                ),
                file=sys.stderr)
        return result


class IngestFileRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/ingest":
            self.send_response(404)
            self.end_headers()
            self.wfile.write("404: Not Found")
            return
        length = int(self.headers.get('content-length'))
        request = json.loads(self.rfile.read(length).decode('utf-8'))
        print("Got request: {}".format(request))
        ingester = IngestFileWorker()
        result = ingester.process(request)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(result))
