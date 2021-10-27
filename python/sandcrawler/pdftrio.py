import time
from typing import Any, Dict, Optional

import requests

from .ia import WaybackClient
from .misc import gen_file_metadata, requests_retry_session
from .workers import SandcrawlerFetchWorker, SandcrawlerWorker


class PdfTrioClient(object):
    def __init__(self, host_url: str = "http://pdftrio.qa.fatcat.wiki", **kwargs):
        self.host_url = host_url
        self.http_session = requests_retry_session(retries=3, backoff_factor=3)

    def classify_pdf(self, blob: bytes, mode: str = "auto") -> Dict[str, Any]:
        """
        Returns a dict with at least:

            - status_code (int, always set)
            - status (success, or error-*)

        On success, the other remote API JSON response keys are also included.

        On HTTP-level failures, the status_code and status field are set
        appropriately; an optional `error_msg` may also be set. For some other
        errors, like connection failure, an exception is raised.
        """
        assert blob and type(blob) == bytes

        try:
            pdftrio_response = requests.post(
                self.host_url + "/classify/research-pub/" + mode,
                files={
                    'pdf_content': blob,
                },
                timeout=60.0,
            )
        except requests.Timeout:
            return {
                'status': 'error-timeout',
                'status_code': -4,  # heritrix3 "HTTP timeout" code
                'error_msg': 'pdftrio request (HTTP POST) timeout',
            }
        except requests.exceptions.ConnectionError:
            # crude back-off
            time.sleep(2.0)
            return {
                'status': 'error-connect',
                'status_code': -2,  # heritrix3 "HTTP connect" code
                'error_msg': 'pdftrio request connection timout',
            }

        info: Dict[str, Any] = dict(status_code=pdftrio_response.status_code)
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


class PdfTrioWorker(SandcrawlerFetchWorker):
    """
    This class is basically copied directly from GrobidWorker
    """
    def __init__(self,
                 pdftrio_client: PdfTrioClient,
                 wayback_client: Optional[WaybackClient] = None,
                 sink: Optional[SandcrawlerWorker] = None,
                 **kwargs):
        super().__init__(wayback_client=wayback_client, **kwargs)
        self.pdftrio_client = pdftrio_client
        self.sink = sink

    def process(self, record: Any, key: str = None) -> Any:
        start_process = time.time()
        fetch_sec = None

        start = time.time()
        fetch_result = self.fetch_blob(record)
        fetch_sec = time.time() - start
        if fetch_result['status'] != 'success':
            return fetch_result
        blob = fetch_result['blob']

        result = dict()
        result['file_meta'] = gen_file_metadata(blob)
        result['key'] = result['file_meta']['sha1hex']
        result['pdf_trio'] = self.pdftrio_client.classify_pdf(blob)
        result['source'] = record
        result['timing'] = dict(
            pdftrio_sec=result['pdf_trio'].pop('_total_sec', None),
            total_sec=time.time() - start_process,
        )
        if fetch_sec:
            result['timing']['fetch_sec'] = fetch_sec
        return result


class PdfTrioBlobWorker(SandcrawlerWorker):
    """
    This is sort of like PdfTrioWorker, except it receives blobs directly,
    instead of fetching blobs from some remote store.
    """
    def __init__(self,
                 pdftrio_client: PdfTrioClient,
                 sink: Optional[SandcrawlerWorker] = None,
                 mode: str = "auto",
                 **kwargs):
        super().__init__(**kwargs)
        self.pdftrio_client = pdftrio_client
        self.sink = sink
        self.mode = mode

    def process(self, blob: Any, key: str = None) -> Any:
        start_process = time.time()
        if not blob:
            return None
        assert isinstance(blob, bytes)
        result = dict()
        result['file_meta'] = gen_file_metadata(blob)
        result['key'] = result['file_meta']['sha1hex']
        result['pdf_trio'] = self.pdftrio_client.classify_pdf(blob, mode=self.mode)
        result['timing'] = dict(
            pdftrio_sec=result['pdf_trio'].pop('_total_sec', None),
            total_sec=time.time() - start_process,
        )
        return result
