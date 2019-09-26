
# XXX: some broken MRO thing going on in here due to python3 object wrangling
# in `wayback` library. Means we can't run pylint.
# pylint: skip-file

import os, sys
import requests

import wayback.exception
from http.client import IncompleteRead
from wayback.resourcestore import ResourceStore
from gwb.loader import CDXLoaderFactory

class CdxApiError(Exception):
    pass

class CdxApiClient:

    def __init__(self, host_url="https://web.archive.org/cdx/search/cdx"):
        self.host_url = host_url

    def lookup_latest(self, url):
        """
        Looks up most recent HTTP 200 record for the given URL.

        Returns a CDX dict, or None if not found.

        XXX: should do authorized lookup using cookie to get all fields
        """

        resp = requests.get(self.host_url, params={
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
            http_status=int(cdx[4]),
            sha1b32=cdx[5],
            sha1hex=b32_hex(cdx[5]),
        )
        return cdx


class WaybackError(Exception):
    pass

class WaybackClient:

    def __init__(self, cdx_client=None, **kwargs):
        if cdx_client:
            self.cdx_client = cdx_client
        else:
            self.cdx_client = CdxApiClient()
        # /serve/ instead of /download/ doesn't record view count
        self.petabox_base_url = kwargs.get('petabox_base_url', 'http://archive.org/serve/')
        # gwb library will fall back to reading from /opt/.petabox/webdata.secret
        self.petabox_webdata_secret = kwargs.get('petabox_webdata_secret', os.environ.get('PETABOX_WEBDATA_SECRET'))
        self.warc_uri_prefix = kwargs.get('warc_uri_prefix', 'https://archive.org/serve/')
        self.rstore = None

    def fetch_warc_content(self, warc_path, offset, c_size):
        warc_uri = self.warc_uri_prefix + warc_path
        if not self.rstore:
            self.rstore = ResourceStore(loaderfactory=CDXLoaderFactory(
                webdata_secret=self.petabox_webdata_secret,
                download_base_url=self.petabox_base_url))
        try:
            gwb_record = self.rstore.load_resource(warc_uri, offset, c_size)
        except wayback.exception.ResourceUnavailable:
            raise WaybackError("failed to load file contents from wayback/petabox (ResourceUnavailable)")
        except ValueError as ve:
            raise WaybackError("failed to load file contents from wayback/petabox (ValueError: {})".format(ve))
        except EOFError as eofe:
            raise WaybackError("failed to load file contents from wayback/petabox (EOFError: {})".format(eofe))
        except TypeError as te:
            raise WaybackError("failed to load file contents from wayback/petabox (TypeError: {}; likely a bug in wayback python code)".format(te))
        # Note: could consider a generic "except Exception" here, as we get so
        # many petabox errors. Do want jobs to fail loud and clear when the
        # whole cluster is down though.

        if gwb_record.get_status()[0] != 200:
            raise WaybackError("archived HTTP response (WARC) was not 200: {}".format(gwb_record.get_status()[0]))

        try:
            raw_content = gwb_record.open_raw_content().read()
        except IncompleteRead as ire:
            raise WaybackError("failed to read actual file contents from wayback/petabox (IncompleteRead: {})".format(ire))
        return raw_content

    def fetch_url_datetime(self, url, datetime):
        cdx_row = self.cdx_client.lookup(url, datetime)
        return self.fetch_warc_content(
            cdx_row['warc_path'],
            cdx_row['warc_offset'],
            cdx_row['warc_csize'])


class SavePageNowError(Exception):
    pass

class SavePageNowClient:

    def __init__(self, cdx_client=None, endpoint="https://web.archive.org/save/"):
        if cdx_client:
            self.cdx_client = cdx_client
        else:
            self.cdx_client = CdxApiClient()
        self.endpoint = endpoint

    def save_url_now(self, url):
        """
        Returns a tuple (cdx, blob) on success, or raises an error on non-success.

        XXX: handle redirects?
        """
        resp = requests.get(self.endpoint + url)
        if resp.status_code != 200:
            raise SavePageNowError("HTTP status: {}, url: {}".format(resp.status_code, url))
        body = resp.content
        cdx = self.cdx_client.lookup_latest(url)
        return (cdx, body)

