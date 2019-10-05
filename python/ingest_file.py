#!/usr/bin/env python3

"""
IngestRequest
  - ingest_type
  - base_url
  - release_stage
  - release_id
  - ext_ids
    - doi
    - pmcid
    - ...
  - expect_mimetypes
  - project/source (?)
  - expect_sha1

FileIngestResult
  - request (object)
  - terminal
    - url
    - status_code
  - wayback
    - datetime
    - archive_url
  - file_meta
    - size_bytes
    - md5
    - sha1
    - sha256
    - mimetype
  - grobid
    - version
    - status_code
    - xml_url
    - release_id
  - status (slug)
  - hit (boolean)

Simplified process, assuming totally new URL and PDF file:

- crawl via SPN (including redirects, extraction)
    => terminal
    => wayback
- calculate file metadata
    => file_meta
- run GROBID
    => grobid

Optimizations:

- sandcrawler-db lookup of base_url: terminal+wayback
- GWB CDX lookup of base_url: terminal+wayback
- sandcrawler-db lookup of GROBID: grobid

New "ingest" table?
- base_url (indexed)
- datetime
- terminal_status
- terminal_url
- terminal_sha1
- hit

"""

import sys
import json
import base64
import hashlib
import argparse
import datetime
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer

from grobid2json import teixml2json


GROBID_ENDPOINT = "http://grobid.qa.fatcat.wiki"

class CDXApiError(Exception):
    pass

class WaybackError(Exception):
    pass

class SavePageNowError(Exception):
    pass

class SandcrawlerDB:

    def __init__(self, **kwargs):
        self.api_uri = kwargs.get('api_url',
            "http://aitio.us.archive.org:3030")

    def get_cdx(self, url):
        resp = requests.get(self.api_url + "/cdx", params=dict(url='eq.'+url))
        resp.raise_for_status()
        return resp.json() or None

    def get_grobid(self, sha1):
        resp = requests.get(self.api_url + "/grobid", params=dict(sha1hex='eq.'+sha1))
        resp.raise_for_status()
        resp = resp.json()
        if resp:
            return resp[0]
        else:
            return None

    def get_file_meta(self, sha1):
        resp = requests.get(self.api_url + "/file_meta", params=dict(sha1hex='eq.'+sha1))
        resp.raise_for_status()
        resp = resp.json()
        if resp:
            return resp[0]
        else:
            return None

def b32_hex(s):
    s = s.strip().split()[0].lower()
    if s.startswith("sha1:"):
        s = s[5:]
    if len(s) != 32:
        return s
    return base64.b16encode(base64.b32decode(s.upper())).lower().decode('utf-8')


def cdx_api_lookup(url):
    """
    Returns a CDX dict, or None if not found.
    """
    CDX_API_ENDPOINT = "https://web.archive.org/cdx/search/cdx"

    resp = requests.get(CDX_API_ENDPOINT, params={
        'url': url,
        'matchType': 'exact',
        'limit': -1,
        'filter': 'statuscode:200',
        'output': 'json',
    })
    if resp.status_code != 200:
        raise CDXApiError(resp.text)
    rj = resp.json()
    if len(rj) <= 1:
        return None
    cdx = rj[1]
    assert len(cdx) == 7    # JSON is short
    cdx = dict(
        surt=cdx[0],
        datetime=cdx[1],
        url=cdx[2],
        mimetype=cdx[3],
        status_code=int(cdx[4]),
        sha1b32=cdx[5],
        sha1hex=b32_hex(cdx[5]),
    )
    return cdx

def parse_html(body):
    raise NotImplementedError()

def save_url_now(url):
    """
    Tries to "save page now"
    """

    SPN_ENDPOINT = "https://web.archive.org/save/"
    resp = requests.get(SPN_ENDPOINT + url)
    if resp.status_code != 200:
        raise SavePageNowError("HTTP status: {}, url: {}".format(resp.status_code, url))
    cdx = cdx_api_lookup(url)
    body = resp.content
    return (cdx, body)

def get_cdx_and_body(url):
    """
    Returns a CDX dict and body as a tuple.

    If there isn't an existing wayback capture, take one now. Raises an
    exception if can't capture, or if CDX API not available.

    Raises an exception if can't find/fetch.

    TODO:
    - doesn't handle redirects (at CDX layer). could allow 3xx status codes and follow recursively
    """

    WAYBACK_ENDPOINT = "https://web.archive.org/web/"

    cdx = cdx_api_lookup(url)
    if not cdx:
        return save_url_now(url)

    resp = requests.get(WAYBACK_ENDPOINT + cdx['datetime'] + "id_/" + cdx['url'])
    if resp.status_code != 200:
        raise WaybackError(resp.text)
    body = resp.content
    return (cdx, body)

def file_metadata(blob):
    """
    Returns a dict: size_bytes, md5, sha1, sha256
    """
    hashes = [
        hashlib.sha1(),
        hashlib.sha256(),
        hashlib.md5(),
    ]
    for h in hashes:
        h.update(blob)
    return dict(
        size_bytes=len(blob),
        sha1=hashes[0].hexdigest(),
        sha256=hashes[1].hexdigest(),
        md5=hashes[2].hexdigest(),
    )


def do_grobid(sha1hex, blob):
    grobid_response = requests.post(
        GROBID_ENDPOINT + "/api/processFulltextDocument",
        files={'input': blob, 'consolidateHeader': '2'},
    )

    info = dict(
        sha1hex=sha1hex,
        status_code=grobid_response.status_code,
    )
    # 4 MByte XML size limit; don't record GROBID status on this path
    if len(grobid_response.content) > 4000000:
        info['status'] = 'oversize'
        return info
    if grobid_response.status_code != 200:
        # response.text is .content decoded as utf-8
        info['status'] = 'error'
        info['error_msg'] = grobid_response.text[:10000]
        dict(status='error', description=grobid_response.text)
        return info, dict(status="error", reason="non-200 GROBID HTTP status",
            extra=grobid_response.text)
    else:
        info['status'] = 'success'

    metadata = teixml2json(grobid_response.text, encumbered=False)
    year = None
    mdate = metadata.get('date')
    if mdate and len(mdate) >= 4:
        year = int(mdate[0:4])
    info['metadata'] = dict(
        title=metadata.get('title'),
        authors=metadata.get('authors'),
        journal=metadata.get('journal'),
        year=metadata.get('year'),
        # TODO: any other biblio-glutton fields? first-page, volume
    )
    info['version'] = metadata.get('grobid_version')
    info['timestamp'] = metadata.get('grobid_timestamp')
    info['glutton_fatcat'] = metadata.get('fatcat_release')
    # TODO: push to kafka
    return info

def ingest_file(request):
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
        (cdx_dict, body) = get_cdx_and_body(url)
        sys.stderr.write("CDX hit: {}\n".format(cdx_dict))

        response['cdx'] = cdx_dict
        response['terminal'] = dict()
        if 'html' in cdx_dict['mimetype']:
            page_metadata = parse_html(body)
            if page_metadata.get('pdf_url'):
                url = page_metadata.get('pdf_url')
                continue
            response['terminal']['html'] = page_metadata
            response['status'] = 'no-pdf-link'
            return response
        elif 'pdf' in cdx_dict['mimetype']:
            break
        else:
            response['status'] = 'other-mimetype'
            return response

    # if we got here, we have a PDF
    response['file_meta'] = file_metadata(body)
    sha1hex = response['file_meta']['sha1']

    # do GROBID
    response['grobid'] = do_grobid(sha1hex, body)
    sys.stderr.write("GROBID status: {}\n".format(response['grobid']['status']))

    # Ok, now what?
    sys.stderr.write("GOT TO END\n")
    response['status'] = "success"
    response['hit'] = True
    return response

def run_single_ingest(args):
    request = dict(
        base_url=args.url,
        ext_ids=dict(doi=args.doi),
        release_id=args.release_id,
    )
    result = ingest_file(request)
    print(json.dumps(result))
    return result

def run_requests(args):
    for l in args.json_file:
        request = json.loads(l.strip())
        result = ingest_file(request)
        print(json.dumps(result))

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
        result = ingest_file(request)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(result))

def run_api(args):
    port = 8083
    print("Listening on localhost:{}".format(port))
    server = HTTPServer(('', port), IngestFileRequestHandler)
    server.serve_forever()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-host-url',
        default="http://localhost:9411/v0",
        help="fatcat API host/port to use")
    subparsers = parser.add_subparsers()

    sub_single= subparsers.add_parser('single')
    sub_single.set_defaults(func=run_single_ingest)
    sub_single.add_argument('--release-id',
        help="(optional) existing release ident to match to")
    sub_single.add_argument('--doi',
        help="(optional) existing release DOI to match to")
    sub_single.add_argument('url',
        help="URL of paper to fetch")

    sub_requests = subparsers.add_parser('requests')
    sub_requests.set_defaults(func=run_requests)
    sub_requests.add_argument('json_file',
        help="JSON file (request per line) to import from (or stdin)",
        default=sys.stdin, type=argparse.FileType('r'))

    sub_api = subparsers.add_parser('api')
    sub_api.set_defaults(func=run_api)
    sub_api.add_argument('--port',
        help="HTTP port to listen on",
        default=8033, type=int)

    args = parser.parse_args()
    if not args.__dict__.get("func"):
        sys.stderr.write("tell me what to do!\n")
        sys.exit(-1)

    args.func(args)

if __name__ == '__main__':
    main()
