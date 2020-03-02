
import sys
import json
import base64
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from collections import namedtuple

from sandcrawler.ia import SavePageNowClient, CdxApiClient, WaybackClient, WaybackError, SavePageNowError, CdxApiError, PetaboxError, cdx_to_dict
from sandcrawler.grobid import GrobidClient
from sandcrawler.misc import gen_file_metadata
from sandcrawler.html import extract_fulltext_url
from sandcrawler.workers import SandcrawlerWorker
from sandcrawler.db import SandcrawlerPostgrestClient


class IngestFileWorker(SandcrawlerWorker):
    """
    High level flow is to look in history first, then go to live web if
    resource not found. Following redirects is treated as "fetching a
    resource". Current version fetches a single resource; if it isn't a hit
    but is an HTML 200, treats it as a landing page, tries to extract
    fulltext link, then fetches that resource.

        process(request) -> response
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

        self.try_existing_ingest = kwargs.get('try_existing_ingest', False)
        self.try_existing_grobid = kwargs.get('try_existing_grobid', True)
        self.try_wayback = kwargs.get('try_wayback', True)
        self.try_spn2 = kwargs.get('try_spn2', True)

        self.base_url_blocklist = [
            # temporary, until we implement specific fetch and 'petabox' output
            "://archive.org/",
            "://web.archive.org/web/",
            "://openlibrary.org/",
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

            # Historical non-paper content:
            "dhz.uni-passau.de/",   # newspapers
            "digital.ucd.ie/",      # ireland national historical
        ]

    def check_existing_ingest(self, base_url):
        """
        Check in sandcrawler-db (postgres) to see if we have already ingested
        this URL (ingest file result table).

        Returns existing row *if* found *and* we should use it, otherwise None.

        Looks at existing ingest results and makes a decision based on, eg,
        status and timestamp.
        """
        if not self.try_existing_ingest:
            return None
        existing = self.pgrest_client.get_ingest_file_result(base_url)
        # TODO: filter on more flags?
        if existing and existing['hit'] == True:
            return existing
        else:
            return None

    def find_resource(self, url, best_mimetype=None):
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

        if self.try_wayback:
            via = "wayback"
            resource = self.wayback_client.lookup_resource(url, best_mimetype)

        # check for "soft 404" conditions, where we should retry with live SPNv2
        # TODO: could refactor these into the resource fetch things themselves?
        soft404 = False
        if resource and resource.hit and resource.terminal_url.endswith('/cookieAbsent'):
            soft404 = True

        if self.try_spn2 and (not resource or not resource.hit or soft404):
            via = "spn2"
            resource = self.spn_client.crawl_resource(url, self.wayback_client)
        print("[FETCH {}\t] {}\t{}".format(
                via,
                resource.status,
                resource.terminal_url or url),
            file=sys.stderr)
        return resource

    def process_existing(self, request, result_row):
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

    def process_hit(self, resource, file_meta):
        """
        Run all the necessary processing for a new/fresh ingest hit.
        """
        return {
            'grobid': self.process_grobid(resource, file_meta),
        }

    def process_grobid(self, resource, file_meta):
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

    def process(self, request):

        # backwards compatibility
        if request.get('ingest_type') in ('file', None):
            request['ingest_type'] = 'pdf'

        # for now, only pdf ingest is implemented
        if not 'ingest_type' in request:
            request['ingest_type'] = "pdf"
        assert request.get('ingest_type') == "pdf"
        ingest_type = request.get('ingest_type')
        base_url = request['base_url']

        for block in self.base_url_blocklist:
            if block in base_url:
                print("[SKIP {}\t] {}".format(ingest_type, base_url), file=sys.stderr)
                return dict(request=request, hit=False, status="skip-url-blocklist")

        print("[INGEST {}\t] {}".format(ingest_type, base_url), file=sys.stderr)

        best_mimetype = None
        if ingest_type == "pdf":
            best_mimetype = "application/pdf"

        existing = self.check_existing_ingest(base_url)
        if existing:
            return self.process_existing(request, existing)

        result = dict(request=request, hit=False)

        next_url = base_url
        hops = [base_url]
        self.max_hops = 6


        while len(hops) <= self.max_hops:

            result['hops'] = hops
            try:
                resource = self.find_resource(next_url, best_mimetype)
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
                return result
            except WaybackError as e:
                result['status'] = 'wayback-error'
                result['error_message'] = str(e)[:1600]
                return result
            except NotImplementedError as e:
                result['status'] = 'not-implemented'
                result['error_message'] = str(e)[:1600]
                return result

            if not resource.hit:
                result['status'] = resource.status
                if resource.terminal_dt and resource.terminal_status_code:
                    result['terminal'] = {
                        "terminal_url": resource.terminal_url,
                        "terminal_dt": resource.terminal_dt,
                        "terminal_status_code": resource.terminal_status_code,
                    }
                    if resource.terminal_url not in result['hops']:
                        result['hops'].append(resource.terminal_url)
                return result

            if not resource.body:
                result['status'] = 'null-body'
                return result
            file_meta = gen_file_metadata(resource.body)

            if "html" in file_meta['mimetype'] or "xhtml" in file_meta['mimetype'] or "application/xml" in file_meta['mimetype']:
                # Got landing page or similar. Some XHTML detected as "application/xml"
                if resource.terminal_dt:
                    result['terminal'] = {
                        "terminal_url": resource.terminal_url,
                        "terminal_dt": resource.terminal_dt,
                        "terminal_status_code": resource.terminal_status_code,
                    }
                fulltext_url = extract_fulltext_url(resource.terminal_url, resource.body)
                
                result['html'] = fulltext_url
                if not fulltext_url:
                    result['status'] = 'no-pdf-link'
                    return result
                next_url = fulltext_url.get('pdf_url') or fulltext_url.get('next_url')
                assert next_url
                print("[PARSE\t] {}\t{}".format(
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
            
            # default is to NOT keep hopping
            break

        if len(hops) >= self.max_hops:
            result['status'] = "max-hops-exceeded"
            return result

        if resource.terminal_dt:
            result['terminal'] = {
                "terminal_url": resource.terminal_url,
                "terminal_dt": resource.terminal_dt,
                "terminal_status_code": resource.terminal_status_code,
                "terminal_sha1hex": file_meta['sha1hex'],
            }

        # fetch must be a hit if we got this far (though not necessarily an ingest hit!)
        assert resource.hit == True
        assert resource.terminal_status_code in (200, 226)

        result['file_meta'] = file_meta
        result['cdx'] = cdx_to_dict(resource.cdx)
        if resource.revisit_cdx:
            result['revisit_cdx'] = cdx_to_dict(resource.revisit_cdx)

        # other failure cases
        if not resource.body or file_meta['size_bytes'] == 0:
            result['status'] = 'null-body'
            return result

        if not (resource.hit and file_meta['mimetype'] == "application/pdf"):
            result['status'] = "wrong-mimetype"  # formerly: "other-mimetype"
            return result

        info = self.process_hit(resource, file_meta)
        result.update(info)

        result['status'] = "success"
        result['hit'] = True
        print("[SUCCESS\t] sha1:{} grobid:{}".format(
                result.get('file_meta', {}).get('sha1hex'),
                result.get('grobid', {}).get('status_code'),
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
