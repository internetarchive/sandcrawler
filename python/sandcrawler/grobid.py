
import requests

from grobid2json import teixml2json
from .workers import SandcrawlerWorker
from .misc import gen_file_metadata
from .ia import WaybackClient, WaybackError

class GrobidClient(object):

    def __init__(self, host_url="http://grobid.qa.fatcat.wiki", **kwargs):
        self.host_url = host_url
        self.consolidate_mode = int(kwargs.get('consolidate_mode', 2))

    def process_fulltext(self, blob, consolidate_mode=None):
        """
        Returns dict with keys:
            - status_code
            - status (slug)
            - error_msg (if status == 'error')
            - tei_xml (if status is 200)

        TODO: persist connection for performance?
        """
        assert blob

        if consolidate_mode == None:
            consolidate_mode = self.consolidate_mode

        try:
            grobid_response = requests.post(
                self.host_url + "/api/processFulltextDocument",
                files={
                    'input': blob,
                    'consolidateHeader': self.consolidate_mode,
                    'consolidateCitations': 0, # too expensive for now
                    'includeRawCitations': 1,
                },
                timeout=180.0,
            )
        except requests.Timeout:
            return {
                'status': 'error-timeout',
                'status': 'GROBID request (HTTP POST) timeout',
            }

        info = dict(
            status_code=grobid_response.status_code,
        )
        if grobid_response.status_code == 200:
            info['status'] = 'success'
            info['tei_xml'] = grobid_response.text
            if len(info['tei_xml']) > 12000000:
                # XML is larger than Kafka message size, and much larger than
                # an article in general; bail out
                info['status'] = 'error'
                info['error_msg'] = "response XML too large: {} bytes".format(len(info['tei_xml']))
                info.pop('tei_xml')
        else:
            # response.text is .content decoded as utf-8
            info['status'] = 'error'
            info['error_msg'] = grobid_response.text[:10000]
        return info

    def metadata(self, result):
        if result['status'] != 'success':
            return None
        tei_json = teixml2json(result['tei_xml'], encumbered=False)
        meta = dict()
        biblio = dict()
        for k in ('title', 'authors', 'journal', 'date', 'doi', ):
            if tei_json.get(k):
                biblio[k] = tei_json[k]
        meta['biblio'] = biblio
        for k in ('grobid_version', 'grobid_timestamp', 'fatcat_release', 'language_code'):
            if tei_json.get(k):
                meta[k] = tei_json[k]
        return meta

class GrobidWorker(SandcrawlerWorker):

    def __init__(self, grobid_client, wayback_client=None, sink=None, **kwargs):
        super().__init__()
        self.grobid_client = grobid_client
        self.wayback_client = wayback_client
        self.sink = sink
        self.consolidate_mode = 2

    def process(self, record):
        if record.get('warc_path') and record.get('warc_offset'):
            # it's a full CDX dict. fetch using WaybackClient
            if not self.wayback_client:
                raise Exception("wayback client not configured for this GrobidWorker")
            try:
                blob = self.wayback_client.fetch_petabox_body(
                    csize=record['warc_csize'],
                    offset=record['warc_offset'],
                    warc_path=record['warc_path'],
                )
            except WaybackError as we:
                return dict(status="error-wayback", error_msg=str(we), source=record)
        elif record.get('url') and record.get('datetime'):
            # it's a partial CDX dict or something? fetch using WaybackClient
            if not self.wayback_client:
                raise Exception("wayback client not configured for this GrobidWorker")
            try:
                blob = self.wayback_client.fetch_replay_body(
                    url=record['url'],
                    datetime=record['datetime'],
                )
            except WaybackError as we:
                return dict(status="error-wayback", error_msg=str(we), source=record)
        elif record.get('item') and record.get('path'):
            # it's petabox link; fetch via HTTP
            resp = requests.get("https://archive.org/serve/{}/{}".format(
                record['item'], record['path']))
            try:
                resp.raise_for_status()
            except Exception as e:
                return dict(status="error-petabox", error_msg=str(e), source=record)
            blob = resp.body
        else:
            raise ValueError("not a CDX (wayback) or petabox (archive.org) dict; not sure how to proceed")
        if not blob:
            return dict(status="error", error_msg="empty blob", source=record)
        result = self.grobid_client.process_fulltext(blob, consolidate_mode=self.consolidate_mode)
        result['file_meta'] = gen_file_metadata(blob)
        result['source'] = record
        result['key'] = result['file_meta']['sha1hex']
        return result

class GrobidBlobWorker(SandcrawlerWorker):
    """
    This is sort of like GrobidWorker, except it receives blobs directly,
    instead of fetching blobs from some remote store.
    """

    def __init__(self, grobid_client, sink=None, **kwargs):
        super().__init__()
        self.grobid_client = grobid_client
        self.sink = sink
        self.consolidate_mode = 2

    def process(self, blob):
        if not blob:
            return None
        result = self.grobid_client.process_fulltext(blob, consolidate_mode=self.consolidate_mode)
        result['file_meta'] = gen_file_metadata(blob)
        result['key'] = result['file_meta']['sha1hex']
        return result

