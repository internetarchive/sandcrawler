
import sys
import json
import base64
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer

from sandcrawler.ia import SavePageNowClient, CdxApiClient, WaybackClient, WaybackError
from sandcrawler.grobid import GrobidClient
from sandcrawler.misc import gen_file_metadata
from sandcrawler.html import extract_fulltext_url
from sandcrawler.workers import SandcrawlerWorker


class IngestFileWorker(SandcrawlerWorker):

    def __init__(self, sink=None, **kwargs):
        super().__init__()
        
        self.sink = sink
        self.spn_client = kwargs.get('spn_client',
            SavePageNowClient())
        self.wayback_client = kwargs.get('wayback_client',
            WaybackClient())
        self.cdx_client = kwargs.get('cdx_client',
            CdxApiClient())
        self.grobid_client = kwargs.get('grobid_client',
            GrobidClient())


    def get_cdx_and_body(self, url):
        """
        Returns a CDX dict and body as a tuple.
    
        If there isn't an existing wayback capture, take one now. Raises an
        exception if can't capture, or if CDX API not available.
    
        Raises an exception if can't find/fetch.
    
        TODO:
        - doesn't handle redirects (at CDX layer). could allow 3xx status codes and follow recursively
        """
    
        WAYBACK_ENDPOINT = "https://web.archive.org/web/"
    
        cdx = self.cdx_client.lookup_latest(url, follow_redirects=True)
        if not cdx:
            # TODO: refactor this to make adding new domains/patterns easier
            # sciencedirect.com (Elsevier) requires browser crawling (SPNv2)
            if ('sciencedirect.com' in url and '.pdf' in url) or ('osapublishing.org' in url) or ('pubs.acs.org/doi/' in url) or ('ieeexplore.ieee.org' in url and ('.pdf' in url or '/stamp/stamp.jsp' in url)):
                #print(url)
                cdx_list = self.spn_client.save_url_now_v2(url)
                for cdx_url in cdx_list:
                    if 'pdf.sciencedirectassets.com' in cdx_url and '.pdf' in cdx_url:
                        cdx = self.cdx_client.lookup_latest(cdx_url)
                        break
                    if 'osapublishing.org' in cdx_url and 'abstract.cfm' in cdx_url:
                        cdx = self.cdx_client.lookup_latest(cdx_url)
                        break
                    if 'pubs.acs.org' in cdx_url and '/doi/pdf/' in cdx_url:
                        cdx = self.cdx_client.lookup_latest(cdx_url)
                        break
                    if 'ieeexplore.ieee.org' in cdx_url and '.pdf' in cdx_url and 'arnumber=' in cdx_url:
                        cdx = self.cdx_client.lookup_latest(cdx_url)
                        break
                if not cdx:
                    # extraction didn't work as expected; fetch whatever SPN2 got
                    cdx = self.cdx_client.lookup_latest(url, follow_redirects=True)
                if not cdx:
                    raise SavePageNowError("")
                    sys.stderr.write("{}\n".format(cdx_list))
                    raise Exception("Failed to crawl PDF URL")
            else:
                return self.spn_client.save_url_now_v1(url)
    
        resp = requests.get(WAYBACK_ENDPOINT + cdx['datetime'] + "id_/" + cdx['url'])
        if resp.status_code != 200:
            raise WaybackError(resp.text)
        body = resp.content
        return (cdx, body)

    def process(self, request):
        """
        1. check sandcrawler-db for base_url
            -> if found, populate terminal+wayback fields
        2. check CDX for base_url (only 200, past year)
            -> if found, populate terminal+wayback fields
        3. if we have wayback, fetch that. otherwise do recursive SPN crawl
            -> populate terminal+wayback
        4. calculate file_meta
            -> populate file_meta
        5. check sandcrawler-db for GROBID XML
        6. run GROBID if we didn't already
            -> push results to minio+sandcrawler-db
        7. decide if this was a hit

        In all cases, print JSON status, and maybe push to sandcrawler-db
        """

        response = dict(request=request)
        url = request['base_url']
        while url:
            (cdx_dict, body) = self.get_cdx_and_body(url)
            sys.stderr.write("CDX hit: {}\n".format(cdx_dict))

            response['cdx'] = cdx_dict
            # TODO: populate terminal
            response['terminal'] = dict(url=cdx_dict['url'], http_status=cdx_dict['http_status'])
            if not body:
                response['status'] = 'null-body'
                return response
            file_meta = gen_file_metadata(body)
            mimetype = cdx_dict['mimetype']
            if mimetype in ('warc/revisit', 'binary/octet-stream', 'application/octet-stream'):
                mimetype = file_meta['mimetype']
                response['file_meta'] = file_meta
            if 'html' in mimetype:
                page_metadata = extract_fulltext_url(response['cdx']['url'], body)
                if page_metadata and page_metadata.get('pdf_url'):
                    next_url = page_metadata.get('pdf_url')
                    if next_url == url:
                        response['status'] = 'link-loop'
                        return response
                    url = next_url
                    continue
                elif page_metadata and page_metadata.get('next_url'):
                    next_url = page_metadata.get('next_url')
                    if next_url == url:
                        response['status'] = 'link-loop'
                        return response
                    url = next_url
                    continue
                else:
                    response['terminal']['html'] = page_metadata
                    response['status'] = 'no-pdf-link'
                return response
            elif 'pdf' in mimetype:
                response['file_meta'] = file_meta
                break
            else:
                response['status'] = 'other-mimetype'
                return response

        # if we got here, we have a PDF
        sha1hex = response['file_meta']['sha1hex']

        # do GROBID
        response['grobid'] = self.grobid_client.process_fulltext(body)
        #sys.stderr.write("GROBID status: {}\n".format(response['grobid']['status']))

        # TODO: optionally publish to Kafka here, but continue on failure (but
        # send a sentry exception?)

        # parse metadata, but drop fulltext from ingest response
        if response['grobid']['status'] == 'success':
            grobid_metadata = self.grobid_client.metadata(response['grobid'])
            if grobid_metadata:
                response['grobid'].update(grobid_metadata)
            response['grobid'].pop('tei_xml')

        # Ok, now what?
        #sys.stderr.write("GOT TO END\n")
        response['status'] = "success"
        response['hit'] = True
        return response

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
        ingester = FileIngestWorker()
        result = ingester.process(request)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(result))
