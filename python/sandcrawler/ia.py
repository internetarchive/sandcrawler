
# XXX: some broken MRO thing going on in here due to python3 object wrangling
# in `wayback` library. Means we can't run pylint.
# pylint: skip-file

import os, sys, time
import requests
import datetime

import wayback.exception
from http.client import IncompleteRead
from wayback.resourcestore import ResourceStore
from gwb.loader import CDXLoaderFactory

from .misc import b32_hex, requests_retry_session

class CdxApiError(Exception):
    pass

class CdxApiClient:

    def __init__(self, host_url="https://web.archive.org/cdx/search/cdx"):
        self.host_url = host_url
        self.http_session = requests_retry_session(retries=3, backoff_factor=3)
        self.http_session.headers.update({
            'User-Agent': 'Mozilla/5.0 sandcrawler.SavePageNowClient',
        })
        self.wayback_endpoint = "https://web.archive.org/web/"

    def lookup_latest(self, url, recent_only=True, follow_redirects=False, redirect_depth=0):
        """
        Looks up most recent HTTP 200 record for the given URL.

        Returns a CDX dict, or None if not found.

        NOTE: could do authorized lookup using cookie to get all fields?
        """

        if redirect_depth >= 15:
            raise CdxApiError("redirect loop (by iteration count)")

        since = datetime.date.today() - datetime.timedelta(weeks=4)
        params = {
            'url': url,
            'matchType': 'exact',
            'limit': -1,
            'output': 'json',
        }
        if recent_only:
            params['from'] = '%04d%02d%02d' % (since.year, since.month, since.day),
        if not follow_redirects:
            params['filter'] = 'statuscode:200'
        resp = self.http_session.get(self.host_url, params=params)
        if resp.status_code != 200:
            raise CdxApiError(resp.text)
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
        if follow_redirects and cdx['http_status'] in (301, 302):
            try:
                resp = requests.get(self.wayback_endpoint + cdx['datetime'] + "id_/" + cdx['url'])
            except requests.exceptions.TooManyRedirects:
                raise CdxApiError("redirect loop (wayback fetch)")
            next_url = '/'.join(resp.url.split('/')[5:])
            if next_url == url:
                raise CdxApiError("redirect loop (by url)")
            return self.lookup_latest(next_url, redirect_depth=redirect_depth+1)
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

class SavePageNowRemoteError(Exception):
    pass

class SavePageNowClient:

    def __init__(self, cdx_client=None,
            v1endpoint="https://web.archive.org/save/",
            v2endpoint="https://web.archive.org/save"):
        if cdx_client:
            self.cdx_client = cdx_client
        else:
            self.cdx_client = CdxApiClient()
        self.ia_access_key = os.environ.get('IA_ACCESS_KEY')
        self.ia_secret_key = os.environ.get('IA_SECRET_KEY')
        self.v1endpoint = v1endpoint
        self.v2endpoint = v2endpoint
        self.v1_session = requests_retry_session(retries=5, backoff_factor=3, status_forcelist=())
        self.v1_session.headers.update({
            'User-Agent': 'Mozilla/5.0 sandcrawler.SavePageNowClient',
        })
        self.v2_session = requests_retry_session(retries=5, backoff_factor=3)
        self.v2_session.headers.update({
            'User-Agent': 'Mozilla/5.0 sandcrawler.SavePageNowClient',
            'Accept': 'application/json',
            'Authorization': 'LOW {}:{}'.format(self.ia_access_key, self.ia_secret_key),
        })

    def save_url_now_v1(self, url):
        """
        Returns a tuple (cdx, blob) on success of single fetch, or raises an
        error on non-success.
        """
        try:
            resp = self.v1_session.get(self.v1endpoint + url)
        except requests.exceptions.RetryError as re:
            # could have been any number of issues...
            raise SavePageNowError(str(re))

        if resp.status_code != 200 and resp.headers.get('X-Archive-Wayback-Runtime-Error'):
            # looks like a weird remote error; would not expect a CDX reply so bailing here
            raise SavePageNowRemoteError(resp.headers['X-Archive-Wayback-Runtime-Error'])
        if resp.status_code != 200 and not resp.headers.get('X-Archive-Orig-Location'):
            # looks like an error which was *not* just a remote server HTTP
            # status code, or one of the handled wayback runtime errors. Some
            # of these are remote server errors that wayback doesn't detect?
            raise SavePageNowError("HTTP status: {}, url: {}".format(resp.status_code, url))

        terminal_url = '/'.join(resp.url.split('/')[5:])
        body = resp.content
        cdx = self.cdx_client.lookup_latest(terminal_url)
        if not cdx:
            raise SavePageNowError("SPN was successful, but CDX lookup then failed. URL: {}".format(terminal_url))
        return (cdx, body)

    def save_url_now_v2(self, url):
        """
        Returns a list of URLs, or raises an error on non-success.
        """
        if not (self.ia_access_key and self.ia_secret_key):
            raise Exception("SPNv2 requires authentication (IA_ACCESS_KEY/IA_SECRET_KEY)")
        resp = self.v2_session.post(
            self.v2endpoint,
            data={
                'url': url,
                'capture_all': 1,
                'if_not_archived_within': '1d',
            },
        )
        if resp.status_code != 200:
            raise SavePageNowError("HTTP status: {}, url: {}".format(resp.status_code, url))
        resp_json = resp.json()
        assert resp_json

        # poll until complete
        final_json = None
        for i in range(90):
            resp = self.v2_session.get("{}/status/{}".format(self.v2endpoint, resp_json['job_id']))
            resp.raise_for_status()
            status = resp.json()['status']
            if status == 'success':
                final_json = resp.json()
                if final_json.get('message', '').startswith('The same snapshot had been made'):
                    raise SavePageNowError("SPN2 re-snapshot within short time window")
                break
            elif status == 'pending':
                time.sleep(1.0)
            else:
                raise SavePageNowError("SPN2 status:{} url:{}".format(status, url))

        if not final_json:
            raise SavePageNowError("SPN2 timed out (polling count exceeded)")

        #print(final_json)
        return final_json['resources']

