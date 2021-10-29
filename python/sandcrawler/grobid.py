from typing import Any, Dict, List, Optional
import sys

import requests
from grobid_tei_xml import GrobidBiblio, parse_citation_list_xml, parse_document_xml

from .ia import WaybackClient
from .misc import gen_file_metadata
from .workers import SandcrawlerFetchWorker, SandcrawlerWorker


class GrobidClient(object):
    def __init__(self, host_url: str = "https://grobid.qa.fatcat.wiki", **kwargs):
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

    def process_citation_list(self, unstructured_list: List[str]) -> List[GrobidBiblio]:
        if not unstructured_list:
            return []
        if len(unstructured_list) > 5000:
            raise ValueError("more than 5,000 references in a batch is just too much")

        try:
            grobid_response = requests.post(
                self.host_url + "/api/processCitationList",
                data={
                    "citations": unstructured_list,
                    "consolidateCitations": 0,
                    "includeRawCitations": 1,
                },
                timeout=30.0,
            )
        except requests.Timeout as te:
            # TODO: handle somehow?
            raise te

        grobid_response.raise_for_status()
        return parse_citation_list_xml(grobid_response.text)

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

    def should_parse_crossref_ref(self, ref: Dict[str, Any]) -> bool:
        """
        Helper function to decide whether to run GROBID parsing on an crossref
        reference.

        For example, if there is already a DOI in the ref metadata, could skip.
        Or, if there is sufficient structured metadata, or only depending on
        the source of the DOI linkage.
        """
        if ref.get("DOI"):
            return False
        if len(ref.get("unstructured", "")) <= 6:
            return False

        # TODO: what other combinations are enough to skip parsing?
        if (
            ref.get("year")
            and ref.get("author")
            and (ref.get("article-title") or ref.get("series-title") or ref.get("volume-title"))
        ):
            return False
        elif ref.get("year") and ref.get("author") and ref.get("journal-title"):
            return False
        elif ref.get("journal-title") and ref.get("volume") and ref.get("first-page"):
            return False

        return True

    def crossref_refs(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Given a complete Crossref metadata record, inspects the

        The returned dict is in the schema of the `grobid_refs` database table,
        in dict form:

            source: 'crossref'
            source_id: doi, as lower-case string
            source_ts: Crossref indexed timestamp, if available
            ('updated' is not set)
            refs_json: list of dicts
        """

        # remove API wrapper around record, if necessary
        if "message" in record and "DOI" not in record:
            record = record["message"]

        ret = dict(
            source="crossref",
            source_id=record["DOI"].lower(),
            source_ts=record["indexed"]["date-time"],
            refs_json=[],
        )
        all_refs = record.get("reference", [])
        unstructured_refs = []
        for r in all_refs:
            if not r.get("unstructured"):
                continue
            if not self.should_parse_crossref_ref(r):
                continue
            unstructured_refs.append(r)
        if not unstructured_refs:
            return ret

        # some reasonable cap on length of refs per work
        if len(unstructured_refs) > 2000:
            print(
                f"truncatin very large reference list for doi:{record['DOI']} len:{len(unstructured_refs)}",
                file=sys.stderr,
            )
            unstructured_refs = unstructured_refs[:2000]

        refs = self.process_citation_list([r["unstructured"] for r in unstructured_refs])
        assert len(refs) == len(unstructured_refs)
        refs_json = []
        for i in range(len(refs)):
            refs[i].id = unstructured_refs[i].get("key")
            assert refs[i].unstructured == unstructured_refs[i]["unstructured"]
            refs_json.append(refs[i].to_dict())
        ret["refs_json"] = refs_json
        return ret


class GrobidWorker(SandcrawlerFetchWorker):
    def __init__(
        self,
        grobid_client: GrobidClient,
        wayback_client: Optional[WaybackClient] = None,
        sink: Optional[SandcrawlerWorker] = None,
        **kwargs,
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


class CrossrefRefsWorker(SandcrawlerWorker):
    def __init__(
        self, grobid_client: GrobidClient, sink: Optional[SandcrawlerWorker] = None, **kwargs
    ):
        super().__init__(**kwargs)
        self.grobid_client = grobid_client
        self.sink = sink

    def process(self, record: Any, key: Optional[str] = None) -> Any:
        return self.grobid_client.crossref_refs(record)


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
