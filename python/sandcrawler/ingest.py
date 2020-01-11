
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

        self.try_existing_ingest = False
        self.try_wayback = True
        self.try_spn2 = True

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
        raise NotImplementedError

        # this "return True" is just here to make pylint happy
        return True

    def find_resource(self, url, best_mimetype=None):
        """
        Looks in wayback for a resource starting at the URL, following any
        redirects. If a hit isn't found, try crawling with SPN.
        """
        via = "none"
        resource = None
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
        result = {
            'hit': result_row.hit,
            'status': result_row.status,
            'request': request,
        }
        # TODO: fetch file_meta
        # TODO: fetch grobid
        return result

    def process_hit(self, resource, file_meta):
        """
        Run all the necessary processing for a new/fresh ingest hit.
        """
        return {
            'grobid': self.process_grobid(resource),
        }

    def process_grobid(self, resource):
        """
        Submits to resource body to GROBID for processing.

        TODO: By default checks sandcrawler-db for an existing row first, then
        decide if we should re-process

        TODO: Code to push to Kafka might also go here?
        """
        result = self.grobid_client.process_fulltext(resource.body)
        if result['status'] == "success":
            metadata = self.grobid_client.metadata(result)
            if metadata:
                result.update(metadata)
        result.pop('tei_xml', None)
        return result

    def process(self, request):

        # backwards compatibility
        if request.get('ingest_type') in ('file', None):
            reqeust['ingest_type'] = 'pdf'

        # for now, only pdf ingest is implemented
        if not 'ingest_type' in request:
            request['ingest_type'] = "pdf"
        assert request.get('ingest_type') == "pdf"
        ingest_type = request.get('ingest_type')
        base_url = request['base_url']

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
                result['error_message'] = str(e)
                return result
            except PetaboxError as e:
                result['status'] = 'petabox-error'
                result['error_message'] = str(e)
                return result
            except CdxApiError as e:
                result['status'] = 'cdx-error'
                result['error_message'] = str(e)
                return result
            except WaybackError as e:
                result['status'] = 'wayback-error'
                result['error_message'] = str(e)
                return result

            if not resource.hit:
                result['status'] = resource.status
                return result
            file_meta = gen_file_metadata(resource.body)

            if "html" in file_meta['mimetype'] or "xml" in file_meta['mimetype']:
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
                print("[EXTRACT\t] {}\t{}".format(
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
            }

        # fetch must be a hit if we got this far (though not necessarily an ingest hit!)
        assert resource.hit == True
        assert resource.terminal_status_code == 200

        result['file_meta'] = file_meta
        result['cdx'] = cdx_to_dict(resource.cdx)

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
