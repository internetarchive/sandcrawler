from typing import Any, Dict, Optional

import requests
from grobid_tei_xml import parse_document_xml

from .ia import WaybackClient
from .misc import gen_file_metadata
from .workers import SandcrawlerFetchWorker, SandcrawlerWorker


class GrobidClient(object):
    def __init__(self, host_url: str = "http://grobid.qa.fatcat.wiki", **kwargs):
        self.host_url = host_url
        self.consolidate_mode = int(kwargs.get("consolidate_mode", 0))

    def process_fulltext(
        self, blob: bytes, consolidate_mode: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Returns dict with keys:
            - status_code
            - status (slug)
            - error_msg (if status == 'error')
            - tei_xml (if status is 200)

        TODO: persist connection for performance?
        """
        assert blob

        if consolidate_mode is None:
            consolidate_mode = self.consolidate_mode
        assert consolidate_mode is not None

        try:
            grobid_response = requests.post(
                self.host_url + "/api/processFulltextDocument",
                files={
                    "input": blob,
                    "consolidateHeader": consolidate_mode,
                    "consolidateCitations": 0,  # too expensive for now
                    "includeRawCitations": 1,
                },
                timeout=180.0,
            )
        except requests.Timeout:
            return {
                "status": "error-timeout",
                "status_code": -4,  # heritrix3 "HTTP timeout" code
                "error_msg": "GROBID request (HTTP POST) timeout",
            }

        info: Dict[str, Any] = dict(status_code=grobid_response.status_code)
        if grobid_response.status_code == 200:
            info["status"] = "success"
            info["tei_xml"] = grobid_response.text
            if len(info["tei_xml"]) > 12000000:
                # XML is larger than Kafka message size, and much larger than
                # an article in general; bail out
                info["status"] = "error"
                info["error_msg"] = "response XML too large: {} bytes".format(
                    len(info["tei_xml"])
                )
                info.pop("tei_xml")
        else:
            # response.text is .content decoded as utf-8
            info["status"] = "error"
            info["error_msg"] = grobid_response.text[:10000]
        return info

    def metadata(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if result["status"] != "success":
            return None
        tei_doc = parse_document_xml(result["tei_xml"])
        tei_doc.remove_encumbered()
        tei_json = tei_doc.to_legacy_dict()
        meta = dict()
        biblio = dict()
        for k in (
            "title",
            "authors",
            "journal",
            "date",
            "doi",
        ):
            if tei_json.get(k):
                biblio[k] = tei_json[k]
        meta["biblio"] = biblio
        for k in ("grobid_version", "grobid_timestamp", "fatcat_release", "language_code"):
            if tei_json.get(k):
                meta[k] = tei_json[k]
        return meta


class GrobidWorker(SandcrawlerFetchWorker):
    def __init__(
        self,
        grobid_client: GrobidClient,
        wayback_client: Optional[WaybackClient] = None,
        sink: Optional[SandcrawlerWorker] = None,
        **kwargs
    ):
        super().__init__(wayback_client=wayback_client)
        self.grobid_client = grobid_client
        self.sink = sink
        self.consolidate_mode = 0

    def timeout_response(self, task: Any) -> Any:
        default_key = task["sha1hex"]
        return dict(
            status="error-timeout",
            error_msg="internal GROBID worker timeout",
            source=task,
            key=default_key,
        )

    def process(self, record: Any, key: Optional[str] = None) -> Any:
        fetch_result = self.fetch_blob(record)
        if fetch_result["status"] != "success":
            return fetch_result
        blob: bytes = fetch_result["blob"]
        assert blob and isinstance(blob, bytes)

        result = self.grobid_client.process_fulltext(
            blob, consolidate_mode=self.consolidate_mode
        )
        result["file_meta"] = gen_file_metadata(blob)
        result["source"] = record
        result["key"] = result["file_meta"]["sha1hex"]
        return result


class GrobidBlobWorker(SandcrawlerWorker):
    """
    This is sort of like GrobidWorker, except it receives blobs directly,
    instead of fetching blobs from some remote store.
    """

    def __init__(
        self, grobid_client: GrobidClient, sink: Optional[SandcrawlerWorker] = None, **kwargs
    ):
        super().__init__()
        self.grobid_client = grobid_client
        self.sink = sink
        self.consolidate_mode = 0

    def process(self, blob: Any, key: Optional[str] = None) -> Any:
        if not blob:
            return None
        result = self.grobid_client.process_fulltext(
            blob, consolidate_mode=self.consolidate_mode
        )
        result["file_meta"] = gen_file_metadata(blob)
        result["key"] = result["file_meta"]["sha1hex"]
        return result
