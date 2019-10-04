
import requests
from collections import Counter

from .workers import SandcrawlerWorker
from .misc import gen_file_metadata
from .ia import WaybackClient, WaybackError

class GrobidClient(object):

    def __init__(self, host_url="http://grobid.qa.fatcat.wiki", **kwargs):
        self.host_url = host_url
        self.consolidate_mode = int(kwargs.get('consolidate_mode', 1))

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

        grobid_response = requests.post(
            self.host_url + "/api/processFulltextDocument",
            files={
                'input': blob,
                'consolidate_mode': self.consolidate_mode,
            }
        )

        info = dict(
            status_code=grobid_response.status_code,
        )
        if grobid_response.status_code == 200:
            info['status'] = 'success'
            info['tei_xml'] = grobid_response.text
        else:
            # response.text is .content decoded as utf-8
            info['status'] = 'error'
            info['error_msg'] = grobid_response.text[:10000]
        return info

class GrobidWorker(SandcrawlerWorker):

    def __init__(self, grobid_client, wayback_client=None, sink=None, **kwargs):
        super().__init__()
        self.grobid_client = grobid_client
        self.wayback_client = wayback_client
        self.sink = sink
        self.consolidate_mode = 1

    def process(self, record):
        if record.get('warc_path') and record.get('warc_offset'):
            # it's a full CDX dict. fetch using WaybackClient
            if not self.wayback_client:
                raise Exception("wayback client not configured for this GrobidWorker")
            try:
                blob = self.wayback_client.fetch_warc_content(record['warc_path'],
                    record['warc_offset'], record['warc_csize'])
            except WaybackError as we:
                return dict(status="error-wayback", error_msg=str(we), source=record)
        elif record.get('url') and record.get('datetime'):
            # it's a partial CDX dict or something? fetch using WaybackClient
            if not self.wayback_client:
                raise Exception("wayback client not configured for this GrobidWorker")
            try:
                blob = self.wayback_client.fetch_url_datetime(record['url'], record['datetime'])
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
        self.consolidate_mode = 1

    def process(self, blob):
        assert blob
        result = self.grobid_client.process_fulltext(blob, consolidate_mode=self.consolidate_mode)
        result['file_meta'] = gen_file_metadata(blob)
        result['key'] = result['file_meta']['sha1hex']
        return result

