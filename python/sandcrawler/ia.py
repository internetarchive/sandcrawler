
# XXX: some broken MRO thing going on in here due to python3 object wrangling
# in `wayback` library. Means we can't run pylint.
# pylint: skip-file

import os, sys, time
import requests
import datetime
from collections import namedtuple

import http.client

# not sure this will really work. Should go before wayback imports.
http.client._MAXHEADERS = 1000  # type: ignore

import wayback.exception
from http.client import IncompleteRead
from wayback.resourcestore import ResourceStore
from gwb.loader import CDXLoaderFactory

from .misc import b32_hex, requests_retry_session, gen_file_metadata, clean_url

class SandcrawlerBackoffError(Exception):
    """
    A set of Exceptions which are raised through multiple abstraction layers to
    indicate backpressure. For example, SPNv2 back-pressure sometimes needs to
    be passed up through any timeout/retry code and become an actual long pause
    or crash.
    """
    pass

ResourceResult = namedtuple("ResourceResult", [
    "start_url",
    "hit",
    "status",
    "terminal_url",
    "terminal_dt",
    "terminal_status_code",
    "body",
    "cdx",
    "revisit_cdx",
])

WarcResource = namedtuple("WarcResource", [
    "status_code",
    "location",
    "body",
    "revisit_cdx",
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

def cdx_to_dict(cdx):
    d = {
        "surt": cdx.surt,
        "datetime": cdx.datetime,
        "url": cdx.url,
        "mimetype": cdx.mimetype,
        "status_code": cdx.status_code,
        "sha1b32": cdx.sha1b32,
        "sha1hex": cdx.sha1hex,
    }
    if type(cdx) == CdxRow and '/' in cdx.warc_path:
        d['warc_csize'] = cdx.warc_csize
        d['warc_offset'] = cdx.warc_offset
        d['warc_path'] = cdx.warc_path
    return d

def fuzzy_match_url(left, right):
    """
    Matches URLs agnostic of http/https (and maybe other normalizations in the
    future)
    """
    if left == right:
        return True
    if '://' in left and '://' in right:
        if left.split('://')[1:] == right.split('://')[1:]:
            return True
    return False

def test_fuzzy_match_url():
    assert fuzzy_match_url("http://thing.com", "http://thing.com") == True
    assert fuzzy_match_url("http://thing.com", "https://thing.com") == True
    assert fuzzy_match_url("http://thing.com", "ftp://thing.com") == True
    assert fuzzy_match_url("http://thing.com", "http://thing.com/blue") == False

    # should probably handle these?
    assert fuzzy_match_url("http://thing.com", "http://thing.com/") == False
    assert fuzzy_match_url("http://thing.com", "http://www.thing.com") == False
    assert fuzzy_match_url("http://www.thing.com", "http://www2.thing.com") == False
    assert fuzzy_match_url("http://www.thing.com", "https://www2.thing.com") == False

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
        #print(resp.url, file=sys.stderr)
        if not resp.text:
            return None
        rj = resp.json()
        if len(rj) <= 1:
            return None
        rows = []
        for raw in rj[1:]:
            assert len(raw) == 11    # JSON is short
            #print(raw, file=sys.stderr)

            # transform "-" ftp status code to a 226
            status_code = None
            if raw[4] == "-":
                if raw[3] != "warc/revisit" and raw[2].startswith("ftp://"):
                    status_code = 226
            else:
                status_code = int(raw[4])

            # CDX rows with no WARC records?
            if raw[8] == '-' or raw[9] == '-' or raw[10] == '-':
                continue

            row = CdxRow(
                surt=raw[0],
                datetime=raw[1],
                url=raw[2],
                mimetype=raw[3],
                status_code=status_code,
                sha1b32=raw[5],
                sha1hex=b32_hex(raw[5]),
                warc_csize=int(raw[8]),
                warc_offset=int(raw[9]),
                warc_path=raw[10],
            )
            assert (row.mimetype == "-") or ("-" not in row)
            rows.append(row)
        return rows

    def fetch(self, url, datetime, filter_status_code=None, retry_sleep=None):
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
            'limit': 1,
            'output': 'json',
        }
        if filter_status_code:
            params['filter'] = "statuscode:{}".format(filter_status_code)
        resp = self._query_api(params)
        if not resp:
            if retry_sleep:
                print("CDX fetch failed; will sleep {}sec and try again".format(retry_sleep), file=sys.stderr)
                time.sleep(retry_sleep)
                return self.fetch(url, datetime, filter_status_code=filter_status_code, retry_sleep=None)
            raise KeyError("CDX url/datetime not found: {} {}".format(url, datetime))
        row = resp[0]
        # allow fuzzy http/https match
        if not (fuzzy_match_url(row.url, url) and row.datetime == datetime):
            if retry_sleep:
                print("CDX fetch failed; will sleep {}sec and try again".format(retry_sleep), file=sys.stderr)
                time.sleep(retry_sleep)
                return self.fetch(url, datetime, filter_status_code=filter_status_code, retry_sleep=None)
            raise KeyError("Didn't get exact CDX url/datetime match. url:{} dt:{} got:{}".format(url, datetime, row))
        if filter_status_code:
            assert row.status_code == filter_status_code
        return row

    def lookup_best(self, url, max_age_days=None, best_mimetype=None):
        """
        Fetches multiple CDX rows for the given URL, tries to find the most recent.

        If no matching row is found, return None. Note this is different from fetch.

        Preference order by status code looks like:

            200 or 226
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

        """
        params = {
            'url': url,
            'matchType': 'exact',
            'limit': -25,
            'output': 'json',
            # Collapsing seems efficient, but is complex; would need to include
            # other filters and status code in filter
            #'collapse': 'timestamp:6',

            # Revisits now allowed and resolved!
            #'filter': '!mimetype:warc/revisit',
        }
        if max_age_days:
            since = datetime.date.today() - datetime.timedelta(days=max_age_days)
            params['from'] = '%04d%02d%02d' % (since.year, since.month, since.day),
        rows = self._query_api(params)
        if not rows:
            return None

        def _cdx_sort_key(r):
            """
            This is a function, not a lambda, because it captures
            best_mimetype. Will create a tuple that can be used to sort in
            *reverse* order.
            """
            return (
                int(r.status_code in (200, 226)),
                int(0 - (r.status_code or 999)),
                int(r.mimetype == best_mimetype),
                int(r.mimetype != "warc/revisit"),
                int('/' in r.warc_path),
                int(r.datetime),
            )

        rows = sorted(rows, key=_cdx_sort_key)
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
        # this *does* want to be http://, not https://
        self.petabox_base_url = kwargs.get('petabox_base_url', 'http://archive.org/serve/')
        # gwb library will fall back to reading from /opt/.petabox/webdata.secret
        self.petabox_webdata_secret = kwargs.get(
            'petabox_webdata_secret',
            os.environ.get('PETABOX_WEBDATA_SECRET'),
        )
        self.warc_uri_prefix = kwargs.get('warc_uri_prefix', 'https://archive.org/serve/')
        self.rstore = None
        self.max_redirects = 25
        self.wayback_endpoint = "https://web.archive.org/web/"
        self.replay_headers = {
            'User-Agent': 'Mozilla/5.0 sandcrawler.WaybackClient',
        }

    def fetch_petabox(self, csize, offset, warc_path, resolve_revisit=True):
        """
        Fetches wayback resource directly from petabox using WARC path/offset/csize.

        If there is a problem with petabox, raises a PetaboxError.
        If resource doesn't exist, would raise a KeyError (TODO).

        The body is only returned if the record is success (HTTP 200 or
        equivalent). Otherwise only the status and header info is returned.

        WarcResource object (namedtuple) contains fields:
        - status_code: int
        - location: eg, for redirects
        - body: raw bytes

        resolve_revist does what it sounds like: tries following a revisit
        record by looking up CDX API and then another fetch. Refuses to recurse
        more than one hop (eg, won't follow a chain of revisits).

        Requires (and uses) a secret token.
        """
        if not self.petabox_webdata_secret:
            raise Exception("WaybackClient needs petabox secret to do direct WARC fetches")
        if not "/" in warc_path:
            raise ValueError("what looks like a liveweb/SPN temporary warc path: {}".format(warc_path))
        warc_uri = self.warc_uri_prefix + warc_path
        if not self.rstore:
            self.rstore = ResourceStore(loaderfactory=CDXLoaderFactory(
                webdata_secret=self.petabox_webdata_secret,
                download_base_url=self.petabox_base_url))
        try:
            #print("offset: {} csize: {} uri: {}".format(offset, csize, warc_uri), file=sys.stderr)
            gwb_record = self.rstore.load_resource(warc_uri, offset, csize)
        except wayback.exception.ResourceUnavailable:
            print("Failed to fetch from warc_path:{}".format(warc_path), file=sys.stderr)
            raise PetaboxError("failed to load file contents from wayback/petabox (ResourceUnavailable)")
        except ValueError as ve:
            raise PetaboxError("failed to load file contents from wayback/petabox (ValueError: {})".format(ve))
        except EOFError as eofe:
            raise PetaboxError("failed to load file contents from wayback/petabox (EOFError: {})".format(eofe))
        except TypeError as te:
            raise PetaboxError("failed to load file contents from wayback/petabox (TypeError: {}; likely a bug in wayback python code)".format(te))
        except Exception as e:
            if "while decompressing data: invalid block type" in str(e):
                raise PetaboxError("decompression error fetching WARC record; usually due to bad alexa ARC files")
            else:
                raise e
        # Note: could consider a generic "except Exception" here, as we get so
        # many petabox errors. Do want jobs to fail loud and clear when the
        # whole cluster is down though.

        try:
            status_code = gwb_record.get_status()[0]
        except http.client.HTTPException:
            raise WaybackError("too many HTTP headers (in wayback fetch)")
        location = gwb_record.get_location() or None

        if status_code is None and gwb_record.target_uri.startswith(b"ftp://") and not gwb_record.is_revisit():
            # TODO: some additional verification here?
            status_code = 226

        body = None
        revisit_cdx = None
        if gwb_record.is_revisit():
            if not resolve_revisit:
                raise WaybackError("found revisit record, but won't resolve (loop?)")
            revisit_uri, revisit_dt = gwb_record.refers_to
            if not (revisit_uri and revisit_dt):
                raise WaybackError("revisit record missing URI and/or DT: warc:{} offset:{}".format(
                    warc_path, offset))
            # convert revisit_dt
            # len("2018-07-24T11:56:49"), or with "Z"
            assert len(revisit_dt) in (19, 20)
            revisit_uri = revisit_uri.decode('utf-8')
            revisit_dt = revisit_dt.decode('utf-8').replace('-', '').replace(':', '').replace('T', '').replace('Z', '')
            assert len(revisit_dt) == 14
            try:
                revisit_cdx = self.cdx_client.fetch(revisit_uri, revisit_dt)
                body = self.fetch_petabox_body(
                    csize=revisit_cdx.warc_csize,
                    offset=revisit_cdx.warc_offset,
                    warc_path=revisit_cdx.warc_path,
                    resolve_revisit=False,
                    expected_status_code=revisit_cdx.status_code,
                )
            except KeyError as ke:
                raise WaybackError("Revist resolution failed: {}".format(ke))
        elif status_code in (200, 226):
            try:
                body = gwb_record.open_raw_content().read()
            except IncompleteRead as ire:
                raise WaybackError(
                    "failed to read actual file contents from wayback/petabox (IncompleteRead: {})".format(ire))
        elif status_code is None:
            raise WaybackError(
                "got a None status_code in (W)ARC record")
        return WarcResource(
            status_code=status_code,
            location=location,
            body=body,
            revisit_cdx=revisit_cdx,
        )

    def fetch_petabox_body(self, csize, offset, warc_path, resolve_revisit=True, expected_status_code=None):
        """
        Fetches HTTP 200 WARC resource directly from petabox using WARC path/offset/csize.

        Returns bytes. Raises KeyError if resource wasn't an HTTP 200.

        Thin helper around fetch_petabox()
        """
        resource = self.fetch_petabox(
            csize=csize,
            offset=offset,
            warc_path=warc_path,
            resolve_revisit=resolve_revisit,
        )

        if expected_status_code:
            if expected_status_code != resource.status_code:
                raise KeyError("archived HTTP response (WARC) was not {}: {}".format(
                    expected_status_code,
                    resource.status_code,
                    )
                )
        elif resource.status_code not in (200, 226):
            raise KeyError("archived HTTP response (WARC) was not 200: {}".format(
                resource.status_code)
            )

        return resource.body

    def fetch_replay_body(self, url, datetime, cdx_sha1hex=None):
        """
        Fetches an HTTP 200 record from wayback via the replay interface
        (web.archive.org) instead of petabox.

        Intended for use with SPN2 requests, where request body has not ended
        up in petabox yet.

        If cdx_sha1hex is passed, will try to verify fetched body. Note that
        this check *won't work* in many cases, due to CDX hash being of
        compressed transfer data, not the uncompressed final content bytes.

        TODO: could instead try to verify that we got the expected replay body
        using... new X-Archive headers?
        """

        # defensively check datetime format
        assert len(datetime) == 14
        assert datetime.isdigit()

        try:
            resp = requests.get(
                self.wayback_endpoint + datetime + "id_/" + url,
                allow_redirects=False,
                headers=self.replay_headers,
            )
        except requests.exceptions.TooManyRedirects:
            raise WaybackError("redirect loop (wayback replay fetch)")
        except requests.exceptions.ChunkedEncodingError:
            raise WaybackError("ChunkedEncodingError (wayback replay fetch)")
        except UnicodeDecodeError:
            raise WaybackError("UnicodeDecodeError in replay request (can mean nasty redirect URL): {}".format(url))

        try:
            resp.raise_for_status()
        except Exception as e:
            raise WaybackError(str(e))
        #print(resp.url, file=sys.stderr)

        # defensively check that this is actually correct replay based on headers
        if not "X-Archive-Src" in resp.headers:
            raise WaybackError("replay fetch didn't return X-Archive-Src in headers")
        if not datetime in resp.url:
            raise WaybackError("didn't get exact reply (redirect?) datetime:{} got:{}".format(datetime, resp.url))

        if cdx_sha1hex:
            # verify that body matches CDX hash
            # TODO: don't need *all* these hashes, just sha1
            file_meta = gen_file_metadata(resp.content)
            if cdx_sha1hex != file_meta['sha1hex']:
                print("REPLAY MISMATCH: cdx:{} replay:{}".format(
                        cdx_sha1hex,
                        file_meta['sha1hex']),
                    file=sys.stderr)
                raise WaybackError("replay fetch body didn't match CDX hash cdx:{} body:{}".format(
                    cdx_sha1hex,
                    file_meta['sha1hex']),
                )
        return resp.content

    def fetch_replay_redirect(self, url, datetime):
        """
        Fetches an HTTP 3xx redirect Location from wayback via the replay interface
        (web.archive.org) instead of petabox.

        Intended for use with SPN2 requests, where request body has not ended
        up in petabox yet. For example, re-ingesting a base_url which was
        recently crawler by SPNv2, where we are doing ingest via wayback path.

        Returns None if response is found, but couldn't find redirect.
        """

        # defensively check datetime format
        assert len(datetime) == 14
        assert datetime.isdigit()

        try:
            resp = requests.get(
                self.wayback_endpoint + datetime + "id_/" + url,
                allow_redirects=False,
                headers=self.replay_headers,
            )
        except requests.exceptions.TooManyRedirects:
            raise WaybackError("redirect loop (wayback replay fetch)")
        except UnicodeDecodeError:
            raise WaybackError("UnicodeDecodeError in replay request (can mean nasty redirect URL): {}".format(url))
        try:
            resp.raise_for_status()
        except Exception as e:
            raise WaybackError(str(e))
        #print(resp.url, file=sys.stderr)

        # defensively check that this is actually correct replay based on headers
        # previously check for "X-Archive-Redirect-Reason" here
        if not "X-Archive-Src" in resp.headers:
            raise WaybackError("redirect replay fetch didn't return X-Archive-Src in headers")
        if not datetime in resp.url:
            raise WaybackError("didn't get exact reply (redirect?) datetime:{} got:{}".format(datetime, resp.url))

        redirect_url = resp.headers.get("Location")
        # eg, https://web.archive.org/web/20200111003923id_/https://dx.doi.org/10.17504/protocols.io.y2gfybw
        #print(redirect_url, file=sys.stderr)
        if redirect_url and redirect_url.startswith("https://web.archive.org/web/"):
            redirect_url = "/".join(redirect_url.split("/")[5:])
        #print(redirect_url, file=sys.stderr)
        if redirect_url and redirect_url.startswith("http"):
            redirect_url = clean_url(redirect_url)
            return redirect_url
        else:
            return None

    def lookup_resource(self, start_url, best_mimetype=None):
        """
        Looks in wayback for a resource starting at the URL, following any
        redirects. Returns a ResourceResult object, which may indicate a
        failure to fetch the resource.

        Only raises exceptions on remote service failure or unexpected
        problems.

        In a for loop:

            lookup "best" CDX
            redirect status code?
                fetch wayback
                continue
            success (200)?
                fetch wayback
                return success
            bad (other status)?
                return failure

        got to end?
            return failure; too many redirects
        """
        next_url = start_url
        urls_seen = [start_url]
        for i in range(self.max_redirects):
            print("  URL: {}".format(next_url), file=sys.stderr)
            cdx_row = self.cdx_client.lookup_best(next_url, best_mimetype=best_mimetype)
            #print(cdx_row, file=sys.stderr)
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
                    revisit_cdx=None,
                )

            # first try straight-forward redirect situation
            if cdx_row.mimetype == "warc/revisit" and '/' in cdx_row.warc_path:
                resource = self.fetch_petabox(
                    csize=cdx_row.warc_csize,
                    offset=cdx_row.warc_offset,
                    warc_path=cdx_row.warc_path,
                )
                if resource.revisit_cdx and resource.revisit_cdx.status_code in (200, 226):
                    return ResourceResult(
                        start_url=start_url,
                        hit=True,
                        status="success",
                        terminal_url=cdx_row.url,
                        terminal_dt=cdx_row.datetime,
                        terminal_status_code=resource.revisit_cdx.status_code, # ?
                        body=resource.body,
                        cdx=cdx_row,
                        revisit_cdx=resource.revisit_cdx,
                    )

            if cdx_row.status_code in (200, 226):
                revisit_cdx = None
                if '/' in cdx_row.warc_path:
                    resource = self.fetch_petabox(
                        csize=cdx_row.warc_csize,
                        offset=cdx_row.warc_offset,
                        warc_path=cdx_row.warc_path,
                    )
                    body = resource.body
                    revisit_cdx = resource.revisit_cdx
                else:
                    body = self.fetch_replay_body(
                        url=cdx_row.url,
                        datetime=cdx_row.datetime,
                    )
                    cdx_row = cdx_partial_from_row(cdx_row)
                return ResourceResult(
                    start_url=start_url,
                    hit=True,
                    status="success",
                    terminal_url=cdx_row.url,
                    terminal_dt=cdx_row.datetime,
                    terminal_status_code=cdx_row.status_code,
                    body=body,
                    cdx=cdx_row,
                    revisit_cdx=revisit_cdx,
                )
            elif 300 <= (cdx_row.status_code or 0) < 400:
                if '/' in cdx_row.warc_path:
                    resource = self.fetch_petabox(
                        csize=cdx_row.warc_csize,
                        offset=cdx_row.warc_offset,
                        warc_path=cdx_row.warc_path,
                        resolve_revisit=False,
                    )
                    assert 300 <= resource.status_code < 400
                    if not resource.location:
                        print("bad redirect record: {}".format(cdx_row), file=sys.stderr)
                        return ResourceResult(
                            start_url=start_url,
                            hit=False,
                            status="bad-redirect",
                            terminal_url=cdx_row.url,
                            terminal_dt=cdx_row.datetime,
                            terminal_status_code=cdx_row.status_code,
                            body=None,
                            cdx=cdx_row,
                            revisit_cdx=None,
                        )
                    if resource.location.startswith('/'):
                        # redirect location does not include hostname
                        domain_prefix = '/'.join(next_url.split('/')[:3])
                        next_url = domain_prefix + resource.location
                    else:
                        next_url = resource.location
                    if next_url:
                        next_url = clean_url(next_url)
                else:
                    next_url = self.fetch_replay_redirect(
                        url=cdx_row.url,
                        datetime=cdx_row.datetime,
                    )
                    if next_url:
                        next_url = clean_url(next_url)
                    cdx_row = cdx_partial_from_row(cdx_row)
                    if not next_url:
                        print("bad redirect record: {}".format(cdx_row), file=sys.stderr)
                        return ResourceResult(
                            start_url=start_url,
                            hit=False,
                            status="bad-redirect",
                            terminal_url=cdx_row.url,
                            terminal_dt=cdx_row.datetime,
                            terminal_status_code=cdx_row.status_code,
                            body=None,
                            cdx=cdx_row,
                            revisit_cdx=None,
                        )
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
                        revisit_cdx=None,
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
                    revisit_cdx=None,
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
            revisit_cdx=None,
        )


class SavePageNowError(Exception):
    pass

class SavePageNowBackoffError(SandcrawlerBackoffError):
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

        # 3 minutes total
        self.poll_count = 60
        self.poll_seconds = 3.0

    def save_url_now_v2(self, request_url, force_get=0, capture_outlinks=0):
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

        TODO: parse SPN error codes (status string) and handle better. Eg,
        non-200 remote statuses, invalid hosts/URLs, timeouts, backoff, etc.
        """
        if capture_outlinks:
            print("  capturing outlinks!", file=sys.stdout)
        if not (self.ia_access_key and self.ia_secret_key):
            raise Exception("SPN2 requires authentication (IA_ACCESS_KEY/IA_SECRET_KEY)")
        if request_url.startswith("ftp://"):
            return SavePageNowResult(
                False,
                "spn2-no-ftp",
                None,
                request_url,
                None,
                None,
                None,
            )
        resp = self.v2_session.post(
            self.v2endpoint,
            data={
                'url': request_url,
                'capture_all': 1,
                'capture_outlinks': capture_outlinks,
                'capture_screenshot': 0,
                'if_not_archived_within': '1d',
                'force_get': force_get,
                'skip_first_archive': 1,
                'outlinks_availability': 0,
            },
        )
        if resp.status_code == 429:
            raise SavePageNowBackoffError("status_code: {}, url: {}".format(resp.status_code, request_url))
        elif resp.status_code != 200:
            raise SavePageNowError("SPN2 status_code: {}, url: {}".format(resp.status_code, request_url))
        resp_json = resp.json()

        if resp_json and 'message' in resp_json and 'You have already reached the limit of active sessions' in resp_json['message']:
            raise SavePageNowBackoffError(resp_json['message'])
        elif not resp_json or 'job_id' not in resp_json:
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

        # if there was a recent crawl of same URL, fetch the status of that
        # crawl to get correct datetime
        if final_json.get('original_job_id'):
            resp = self.v2_session.get("{}/status/{}".format(self.v2endpoint, final_json['original_job_id']))
            try:
                resp.raise_for_status()
            except:
                raise SavePageNowError(resp.content)
            final_json = resp.json()

        #print(final_json, file=sys.stderr)

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
            if final_json['status'] == 'pending':
                final_json['status'] = 'error:pending'
            return SavePageNowResult(
                False,
                final_json.get('status_ext') or final_json['status'],
                job_id,
                request_url,
                None,
                None,
                None,
            )

    def crawl_resource(self, start_url, wayback_client, force_get=0):
        """
        Runs a SPN2 crawl, then fetches body from wayback.

        TODO: possible to fetch from petabox?
        """

        # HACK: capture CNKI domains with outlinks (for COVID-19 crawling)
        if 'gzbd.cnki.net/' in start_url:
            spn_result = self.save_url_now_v2(start_url, force_get=force_get, capture_outlinks=1)
        else:
            spn_result = self.save_url_now_v2(start_url, force_get=force_get)

        if not spn_result.success:
            status = spn_result.status
            if status in ("error:invalid-url", "error:not-found",
                    "error:invalid-host-resolution", "error:gateway-timeout"):
                status = status.replace("error:", "")
            elif status == "error:no-access":
                status = "forbidden"
            elif status == "error:user-session-limit":
                raise SavePageNowBackoffError("SPNv2 user-session-limit")
            elif status.startswith("error:"):
                status = "spn2-" + status
            return ResourceResult(
                start_url=start_url,
                hit=False,
                status=status,
                terminal_url=spn_result.terminal_url,
                terminal_dt=spn_result.terminal_dt,
                terminal_status_code=None,
                body=None,
                cdx=None,
                revisit_cdx=None,
            )
        #print(spn_result, file=sys.stderr)

        cdx_row = None
        # hack to work around elsevier weirdness
        if "://pdf.sciencedirectassets.com/" in spn_result.request_url:
            elsevier_pdf_cdx = wayback_client.cdx_client.lookup_best(
                spn_result.request_url,
                best_mimetype="application/pdf",
            )
            if elsevier_pdf_cdx and elsevier_pdf_cdx.mimetype == "application/pdf":
                print("Trying pdf.sciencedirectassets.com hack!", file=sys.stderr)
                cdx_row = elsevier_pdf_cdx
            else:
                print("Failed pdf.sciencedirectassets.com hack!", file=sys.stderr)
                #print(elsevier_pdf_cdx, file=sys.stderr)

        if not cdx_row:
            # lookup exact
            try:
                filter_status_code = 200
                if spn_result.terminal_url.startswith("ftp://"):
                    filter_status_code = 226
                cdx_row = wayback_client.cdx_client.fetch(
                    url=spn_result.terminal_url,
                    datetime=spn_result.terminal_dt,
                    filter_status_code=filter_status_code,
                    retry_sleep=10.0,
                )
            except KeyError as ke:
                print("CDX KeyError: {}".format(ke), file=sys.stderr)
                return ResourceResult(
                    start_url=start_url,
                    hit=False,
                    status="spn2-cdx-lookup-failure",
                    terminal_url=spn_result.terminal_url,
                    terminal_dt=spn_result.terminal_dt,
                    terminal_status_code=None,
                    body=None,
                    cdx=None,
                    revisit_cdx=None,
                )

        #print(cdx_row, file=sys.stderr)

        revisit_cdx = None
        if '/' in cdx_row.warc_path:
            # Usually can't do this kind of direct fetch because CDX result is recent/live
            resource = wayback_client.fetch_petabox(
                csize=cdx_row.warc_csize,
                offset=cdx_row.warc_offset,
                warc_path=cdx_row.warc_path,
            )
            body = resource.body
            if resource.revisit_cdx:
                assert resource.revisit_cdx.sha1hex == cdx_row.sha1hex
                revisit_cdx = resource.revisit_cdx
        else:
            # note: currently not trying to verify cdx_row.sha1hex
            body = wayback_client.fetch_replay_body(
                url=cdx_row.url,
                datetime=cdx_row.datetime,
            )
            # warc_path etc will change, so strip them out
            cdx_row = cdx_partial_from_row(cdx_row)

        return ResourceResult(
            start_url=start_url,
            hit=True,
            status="success",
            terminal_url=cdx_row.url,
            terminal_dt=cdx_row.datetime,
            terminal_status_code=cdx_row.status_code,
            body=body,
            cdx=cdx_row,
            revisit_cdx=revisit_cdx,
        )

