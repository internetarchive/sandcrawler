
import time
import requests

from .workers import SandcrawlerWorker
from .misc import gen_file_metadata, requests_retry_session
from .ia import WaybackClient, WaybackError, PetaboxError


class PdfTrioClient(object):

    def __init__(self, host_url="http://pdftrio.qa.fatcat.wiki", **kwargs):
        self.host_url = host_url
        self.http_session = requests_retry_session(retries=3, backoff_factor=3)

    def classify_pdf(self, blob, mode="auto"):
        """
        Returns a dict with at least:

            - status_code (int, always set)
            - status (success, or error-*)

        On success, the other remote API JSON response keys are also included.

        On HTTP-level failures, the status_code and status field are set
        appropriately; an optional `error_msg` may also be set. For some other
        errors, like connection failure, an exception is raised.
        """
        assert blob

        try:
            pdftrio_response = requests.post(
                self.host_url + "/classify/research-pub/" + mode,
                files={
                    'pdf_content': blob,
                },
                timeout=30.0,
            )
        except requests.Timeout:
            return {
                'status': 'error-timeout',
                'status_code': -4,  # heritrix3 "HTTP timeout" code
                'error_msg': 'pdftrio request (HTTP POST) timeout',
            }

        info = dict(
            status_code=pdftrio_response.status_code,
        )
        if pdftrio_response.status_code == 200:
            resp_json = pdftrio_response.json()
            assert 'ensemble_score' in resp_json
            assert 'status' in resp_json
            assert 'versions' in resp_json
            info.update(resp_json)
        else:
            info['status'] = 'error'
            # TODO: might return JSON with some info?

        info['_total_sec'] = pdftrio_response.elapsed.total_seconds()
        return info


class PdfTrioWorker(SandcrawlerWorker):
    """
    This class is basically copied directly from GrobidWorker
    """

    def __init__(self, pdftrio_client, wayback_client=None, sink=None, **kwargs):
        super().__init__()
        self.pdftrio_client = pdftrio_client
        self.wayback_client = wayback_client
        self.sink = sink

    def process(self, record):
        start_process = time.time()
        default_key = record['sha1hex']
        wayback_sec = None
        petabox_sec = None
        if record.get('warc_path') and record.get('warc_offset'):
            # it's a full CDX dict. fetch using WaybackClient
            if not self.wayback_client:
                raise Exception("wayback client not configured for this PdfTrioWorker")
            try:
                start = time.time()
                blob = self.wayback_client.fetch_petabox_body(
                    csize=record['warc_csize'],
                    offset=record['warc_offset'],
                    warc_path=record['warc_path'],
                )
                wayback_sec = time.time() - start
            except (WaybackError, PetaboxError) as we:
                return dict(
                    key=default_key,
                    source=record,
                    pdf_trio=dict(
                        status="error-wayback",
                        error_msg=str(we),
                    ),
                )
        elif record.get('url') and record.get('datetime'):
            # it's a partial CDX dict or something? fetch using WaybackClient
            if not self.wayback_client:
                raise Exception("wayback client not configured for this PdfTrioWorker")
            try:
                start = time.time()
                blob = self.wayback_client.fetch_replay_body(
                    url=record['url'],
                    datetime=record['datetime'],
                )
                wayback_sec = time.time() - start
            except WaybackError as we:
                return dict(
                    key=default_key,
                    source=record,
                    pdf_trio=dict(
                        status="error-wayback",
                        error_msg=str(we),
                    ),
                )
        elif record.get('item') and record.get('path'):
            # it's petabox link; fetch via HTTP
            start = time.time()
            resp = requests.get("https://archive.org/serve/{}/{}".format(
                record['item'], record['path']))
            petabox_sec = time.time() - start
            try:
                resp.raise_for_status()
            except Exception as e:
                return dict(
                    key=default_key,
                    source=record,
                    pdf_trio=dict(
                        status="error-petabox",
                        error_msg=str(e),
                    ),
                )
            blob = resp.content
        else:
            raise ValueError("not a CDX (wayback) or petabox (archive.org) dict; not sure how to proceed")
        if not blob:
            return dict(
                key=default_key,
                source=record,
                pdf_trio=dict(
                    status="error",
                    error_msg="empty blob",
                ),
            )
        result = dict()
        result['file_meta'] = gen_file_metadata(blob)
        result['key'] = result['file_meta']['sha1hex']
        result['pdf_trio'] = self.pdftrio_client.classify_pdf(blob)
        result['source'] = record
        result['timing'] = dict(
            pdftrio_sec=result['pdf_trio'].pop('_total_sec', None),
            total_sec=time.time() - start_process,
        )
        if wayback_sec:
            result['timing']['wayback_sec'] = wayback_sec
        if petabox_sec:
            result['timing']['petabox_sec'] = wayback_sec
        return result

class PdfTrioBlobWorker(SandcrawlerWorker):
    """
    This is sort of like PdfTrioWorker, except it receives blobs directly,
    instead of fetching blobs from some remote store.
    """

    def __init__(self, pdftrio_client, sink=None, mode="auto", **kwargs):
        super().__init__()
        self.pdftrio_client = pdftrio_client
        self.sink = sink
        self.mode = mode

    def process(self, blob):
        start_process = time.time()
        if not blob:
            return None
        result = dict()
        result['file_meta'] = gen_file_metadata(blob)
        result['key'] = result['file_meta']['sha1hex']
        result['pdf_trio'] = self.pdftrio_client.classify_pdf(blob, mode=mode)
        result['timing'] = dict(
            pdftrio_sec=result['pdf_trio'].pop('_total_sec', None),
            total_sec=time.time() - start_process,
        )
        return result

