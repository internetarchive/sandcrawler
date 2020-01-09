
# XXX: some broken MRO thing going on in here due to python3 object wrangling
# in `wayback` library. Means we can't run pylint.
# pylint: skip-file

import os, sys, time
import requests
import datetime
from collections import namedtuple

import wayback.exception
from http.client import IncompleteRead
from wayback.resourcestore import ResourceStore
from gwb.loader import CDXLoaderFactory

from .misc import b32_hex, requests_retry_session, gen_file_metadata


ResourceResult = namedtuple("ResourceResult", [
    "start_url",
    "hit",
    "status",
    "terminal_url",
    "terminal_dt",
    "terminal_status_code",
    "body",
    "cdx",
])

WarcResource = namedtuple("WarcResource", [
    "status_code",
    "location",
    "body",
])

CdxRow = namedtuple('CdxRow', [
    'surt',
    'datetime',
    'url',
    'mimetype',
    'status_code',
    'sha1b32',
    'sha1hex',
    'warc_csize',
    'warc_offset',
    'warc_path',
])

CdxPartial = namedtuple('CdxPartial', [
    'surt',
    'datetime',
    'url',
    'mimetype',
    'status_code',
    'sha1b32',
    'sha1hex',
])

def cdx_partial_from_row(full):
    return CdxPartial(
        surt=full.surt,
        datetime=full.datetime,
        url=full.url,
        mimetype=full.mimetype,
        status_code=full.status_code,
        sha1b32=full.sha1b32,
        sha1hex=full.sha1hex,
    )


class CdxApiError(Exception):
    pass

class CdxApiClient:

    def __init__(self, host_url="https://web.archive.org/cdx/search/cdx", **kwargs):
        self.host_url = host_url
        self.http_session = requests_retry_session(retries=3, backoff_factor=3)
        cdx_auth_token = kwargs.get('cdx_auth_token',
            os.environ.get('CDX_AUTH_TOKEN'))
        if not cdx_auth_token:
            raise Exception("CDX auth token required (as parameter or environment variable CDX_AUTH_TOKEN)")
        self.http_session.headers.update({
            'User-Agent': 'Mozilla/5.0 sandcrawler.CdxApiClient',
            'Cookie': 'cdx_auth_token={}'.format(cdx_auth_token),
        })

    def _query_api(self, params):
        """
        Hits CDX API with a query, parses result into a list of CdxRow
        """
        resp = self.http_session.get(self.host_url, params=params)
        if resp.status_code != 200:
            raise CdxApiError(resp.text)
        rj = resp.json()
        if len(rj) <= 1:
            return None
        rows = []
        for raw in rj[1:]:
            assert len(raw) == 11    # JSON is short
            row = CdxRow(
                surt=raw[0],
                datetime=raw[1],
                url=raw[2],
                mimetype=raw[3],
                status_code=int(raw[4]),
                sha1b32=raw[5],
                sha1hex=b32_hex(raw[5]),
                warc_csize=int(raw[8]),
                warc_offset=int(raw[9]),
                warc_path=raw[10],
            )
            assert (row.mimetype == "-") or ("-" not in row)
            rows.append(row)
        return rows

    def fetch(self, url, datetime, filter_status_code=None):
        """
        Fetches a single CDX row by url/datetime. Raises a KeyError if not
        found, because we expect to be looking up a specific full record.
        """
        if len(datetime) != 14:
            raise ValueError("CDX fetch requires full 14 digit timestamp. Got: {}".format(datetime))
        params = {
            'url': url,
            'from': datetime,
            'to': datetime,
            'matchType': 'exact',
            'limit': -1,
            'output': 'json',
        }
        if filter_status_code:
            params['filter'] = "statuscode:{}".format(filter_status_code)
        resp = self._query_api(params)
        if not resp:
            raise KeyError("CDX url/datetime not found: {} {}".format(url, datetime))
        row = resp[0]
        if not (row.url == url and row.datetime == datetime):
            raise KeyError("CDX url/datetime not found: {} {} (closest: {})".format(url, datetime, row))
        return row

    def lookup_best(self, url, max_age_days=None, best_mimetype=None):
        """
        Fetches multiple CDX rows for the given URL, tries to find the most recent.

        If no matching row is found, return None. Note this is different from fetch.
        """
        params = {
            'url': url,
            'matchType': 'exact',
            'limit': -25,
            'output': 'json',
            'collapse': 'timestamp:6',
            'filter': '!mimetype:warc/revisit',
        }
        if max_age_days:
            since = datetime.date.today() - datetime.timedelta(days=max_age_days)
            params['from'] = '%04d%02d%02d' % (since.year, since.month, since.day),
        rows = self._query_api(params)
        if not rows:
            return None

        def cdx_sort_key(r):
            """
            Preference order by status code looks like:

                200
                    mimetype match
                        not-liveweb
                            most-recent
                    no match
                        not-liveweb
                            most-recent
                3xx
                    most-recent
                4xx
                    most-recent
                5xx
                    most-recent

            This function will create a tuple that can be used to sort in *reverse* order.
            """
            return (
                int(r.status_code == 200),
                int(0 - r.status_code),
                int(r.mimetype == best_mimetype),
                int('/' in r.warc_path),
                int(r.datetime),
            )

        rows = sorted(rows, key=cdx_sort_key)
        return rows[-1]


class WaybackError(Exception):
    pass

class PetaboxError(Exception):
    pass

class WaybackClient:

    def __init__(self, cdx_client=None, **kwargs):
        if cdx_client:
            self.cdx_client = cdx_client
        else:
            self.cdx_client = CdxApiClient()
        # /serve/ instead of /download/ doesn't record view count
        self.petabox_base_url = kwargs.get('petabox_base_url', 'https://archive.org/serve/')
        # gwb library will fall back to reading from /opt/.petabox/webdata.secret
        self.petabox_webdata_secret = kwargs.get('petabox_webdata_secret', os.environ.get('PETABOX_WEBDATA_SECRET'))
        self.warc_uri_prefix = kwargs.get('warc_uri_prefix', 'https://archive.org/serve/')
        self.rstore = None
        self.max_redirects = 25

    def fetch_petabox(self, c_size, offset, warc_path):
        """
        Fetches wayback resource directly from petabox using WARC path/offset/csize.

        If there is a problem with petabox, raises a PetaboxError.
        If resource doesn't exist, would raise a KeyError (TODO).

        The full record is returned as crawled; it may be a redirect, 404
        response, etc.

        WarcResource object (namedtuple) contains fields:
        - status_code: int
        - location: eg, for redirects
        - body: raw bytes

        Requires (and uses) a secret token.
        """
        if not self.petabox_webdata_secret:
            raise Exception("WaybackClient needs petabox secret to do direct WARC fetches")
        # TODO:
        #if not "/" in warc_path:
        #    raise ValueError("what looks like a liveweb/SPN temporary warc path: {}".format(warc_path))
        warc_uri = self.warc_uri_prefix + warc_path
        if not self.rstore:
            self.rstore = ResourceStore(loaderfactory=CDXLoaderFactory(
                webdata_secret=self.petabox_webdata_secret,
                download_base_url=self.petabox_base_url))
        try:
            gwb_record = self.rstore.load_resource(warc_uri, offset, c_size)
        except wayback.exception.ResourceUnavailable:
            raise PetaboxError("failed to load file contents from wayback/petabox (ResourceUnavailable)")
        except ValueError as ve:
            raise PetaboxError("failed to load file contents from wayback/petabox (ValueError: {})".format(ve))
        except EOFError as eofe:
            raise PetaboxError("failed to load file contents from wayback/petabox (EOFError: {})".format(eofe))
        except TypeError as te:
            raise PetaboxError("failed to load file contents from wayback/petabox (TypeError: {}; likely a bug in wayback python code)".format(te))
        # Note: could consider a generic "except Exception" here, as we get so
        # many petabox errors. Do want jobs to fail loud and clear when the
        # whole cluster is down though.

        status_code = gwb_record.get_status()[0]
        location = (gwb_record.get_location() or [None])[0]

        body = None
        if status_code == 200:
            try:
                body = gwb_record.open_raw_content().read()
            except IncompleteRead as ire:
                raise WaybackError("failed to read actual file contents from wayback/petabox (IncompleteRead: {})".format(ire))
        return WarcResource(
            status_code=status_code,
            location=location,
            body=body,
        )

    def fetch_petabox_body(self, c_size, offset, warc_path):
        """
        Fetches HTTP 200 WARC resource directly from petabox using WARC path/offset/csize.

        Returns bytes. Raises KeyError if resource wasn't an HTTP 200.

        Thin helper around fetch_petabox()
        """
        resource = self.fetch_petabox(c_size, offset, warc_path)

        if resource.status_code != 200:
            raise KeyError("archived HTTP response (WARC) was not 200: {}".format(gwb_record.get_status()[0]))

        return resource.body

    def fetch_replay_body(self, url, datetime):
        """
        Fetches an HTTP 200 record from wayback via the replay interface
        (web.archive.org) instead of petabox.

        Intended for use with SPN2 requests, where request body has not ended
        up in petabox yet.

        TODO: is this actually necessary?
        """
        raise NotImplementedError

    def lookup_resource(self, start_url, best_mimetype=None):
        """
        Looks in wayback for a resource starting at the URL, following any
        redirects. Returns a ResourceResult object.

        In a for loop:

            lookup best CDX
            redirect?
                fetch wayback
                continue
            good?
                fetch wayback
                return success
            bad?
                return failure

        got to end?
            return failure; too many redirects
        """
        next_url = start_url
        urls_seen = [start_url]
        for i in range(self.max_redirects):
            cdx_row = self.cdx_client.lookup_best(next_url, best_mimetype=best_mimetype)
            if not cdx_row:
                return ResourceResult(
                    start_url=start_url,
                    hit=False,
                    status="no-capture",
                    terminal_url=None,
                    terminal_dt=None,
                    terminal_status_code=None,
                    body=None,
                    cdx=None,
                )
            if cdx_row.status_code == 200:
                body = self.fetch_petabox_body(cdx_row.warc_csize, cdx_row.warc_offset, cdx_row.warc_path)
                return ResourceResult(
                    start_url=start_url,
                    hit=True,
                    status="success",
                    terminal_url=cdx_row.url,
                    terminal_dt=cdx_row.datetime,
                    terminal_status_code=cdx_row.status_code,
                    body=body,
                    cdx=cdx_row,
                )
            elif 300 <= cdx_row.status_code < 400:
                resource = self.fetch_petabox(cdx_row.warc_csize, cdx_row.warc_offset, cdx_row.warc_path)
                assert 300 <= resource.status_code < 400
                next_url = resource.location
                if next_url in urls_seen:
                    return ResourceResult(
                        start_url=start_url,
                        hit=False,
                        status="redirect-loop",
                        terminal_url=cdx_row.url,
                        terminal_dt=cdx_row.datetime,
                        terminal_status_code=cdx_row.status_code,
                        body=None,
                        cdx=cdx_row,
                    )
                urls_seen.append(next_url)
                continue
            else:
                return ResourceResult(
                    start_url=start_url,
                    hit=False,
                    status="terminal-bad-status",
                    terminal_url=cdx_row.url,
                    terminal_dt=cdx_row.datetime,
                    terminal_status_code=cdx_row.status_code,
                    body=None,
                    cdx=cdx_row,
                )
        return ResourceResult(
            start_url=start_url,
            hit=False,
            status="redirects-exceeded",
            terminal_url=cdx_row.url,
            terminal_dt=cdx_row.datetime,
            terminal_status_code=cdx_row.status_code,
            body=None,
            cdx=cdx_row,
        )


class SavePageNowError(Exception):
    pass

SavePageNowResult = namedtuple('SavePageNowResult', [
    'success',
    'status',
    'job_id',
    'request_url',
    'terminal_url',
    'terminal_dt',
    'resources',
])

class SavePageNowClient:

    def __init__(self, v2endpoint="https://web.archive.org/save", **kwargs):
        self.ia_access_key = kwargs.get('ia_access_key',
            os.environ.get('IA_ACCESS_KEY'))
        self.ia_secret_key = kwargs.get('ia_secret_key',
            os.environ.get('IA_SECRET_KEY'))
        self.v2endpoint = v2endpoint
        self.v2_session = requests_retry_session(retries=5, backoff_factor=3)
        self.v2_session.headers.update({
            'User-Agent': 'Mozilla/5.0 sandcrawler.SavePageNowClient',
            'Accept': 'application/json',
            'Authorization': 'LOW {}:{}'.format(self.ia_access_key, self.ia_secret_key),
        })
        self.poll_count = 30
        self.poll_seconds = 3.0

    def save_url_now_v2(self, request_url):
        """
        Returns a "SavePageNowResult" (namedtuple) if SPN request was processed
        at all, or raises an exception if there was an error with SPN itself.

        If SPN2 was unable to fetch the remote content, `success` will be
        false and status will be indicated.

        SavePageNowResult fields:
        - success: boolean if SPN
        - status: "success" or an error message/type
        - job_id: returned by API
        - request_url: url we asked to fetch
        - terminal_url: final primary resource (after any redirects)
        - terminal_dt: wayback timestamp of final capture
        - resources: list of all URLs captured

        TODO: parse SPN error codes and handle better. Eg, non-200 remote
        statuses, invalid hosts/URLs, timeouts, backoff, etc.
        """
        if not (self.ia_access_key and self.ia_secret_key):
            raise Exception("SPN2 requires authentication (IA_ACCESS_KEY/IA_SECRET_KEY)")
        resp = self.v2_session.post(
            self.v2endpoint,
            data={
                'url': request_url,
                'capture_all': 1,
                'if_not_archived_within': '1d',
            },
        )
        if resp.status_code != 200:
            raise SavePageNowError("SPN2 status_code: {}, url: {}".format(resp.status_code, request_url))
        resp_json = resp.json()

        if not resp_json or 'job_id' not in resp_json:
            raise SavePageNowError(
                "Didn't get expected 'job_id' field in SPN2 response: {}".format(resp_json))

        job_id = resp_json['job_id']

        # poll until complete
        final_json = None
        for i in range(self.poll_count):
            resp = self.v2_session.get("{}/status/{}".format(self.v2endpoint, resp_json['job_id']))
            try:
                resp.raise_for_status()
            except:
                raise SavePageNowError(resp.content)
            status = resp.json()['status']
            if status == 'pending':
                time.sleep(self.poll_seconds)
            elif status in ('success', 'error'):
                final_json = resp.json()
                break
            else:
                raise SavePageNowError("Unknown SPN2 status:{} url:{}".format(status, request_url))

        if not final_json:
            raise SavePageNowError("SPN2 timed out (polling count exceeded)")

        if final_json['status'] == "success":
            return SavePageNowResult(
                True,
                "success",
                job_id,
                request_url,
                final_json['original_url'],
                final_json['timestamp'],
                final_json['resources'],
            )
        else:
            return SavePageNowResult(
                False,
                final_json.get('status_ext') or final_json['status'],
                job_id,
                request_url,
                None,
                None,
                None,
            )

    def crawl_resource(self, start_url, wayback_client):
        """
        Runs a SPN2 crawl, then fetches body from wayback.

        TODO: possible to fetch from petabox?
        """

        spn_result = self.save_url_now_v2(start_url)

        if not spn_result.success:
            return ResourceResult(
                start_url=start_url,
                hit=False,
                status=spn_result.status,
                terminal_url=spn_result.terminal_url,
                terminal_dt=spn_result.terminal_dt,
                terminal_status_code=None,
                body=None,
                cdx=None,
            )

        # fetch CDX and body
        cdx_row = wayback_client.cdx_client.fetch(spn_result.terminal_url, spn_result.terminal_dt)
        assert cdx_row.status_code == 200
        body = wayback_client.fetch_petabox_body(cdx_row.warc_csize, cdx_row.warc_offset, cdx_row.warc_path)

        # not a full CDX yet
        cdx_partial = cdx_partial_from_row(cdx_row)
        return ResourceResult(
            start_url=start_url,
            hit=True,
            status="success",
            terminal_url=cdx_row.url,
            terminal_dt=cdx_row.datetime,
            terminal_status_code=cdx_row.status_code,
            body=body,
            cdx=cdx_partial,
        )

