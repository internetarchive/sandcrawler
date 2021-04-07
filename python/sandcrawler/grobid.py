
import requests

from grobid2json import teixml2json
from .workers import SandcrawlerWorker, SandcrawlerFetchWorker
from .misc import gen_file_metadata

class GrobidClient(object):

    def __init__(self, host_url="http://grobid.qa.fatcat.wiki", **kwargs):
        self.host_url = host_url
        self.consolidate_mode = int(kwargs.get('consolidate_mode', 0))

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
                'status_code': -4,  # heritrix3 "HTTP timeout" code
                'error_msg': 'GROBID request (HTTP POST) timeout',
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

class GrobidWorker(SandcrawlerFetchWorker):

    def __init__(self, grobid_client, wayback_client=None, sink=None, **kwargs):
        super().__init__(wayback_client=wayback_client)
        self.grobid_client = grobid_client
        self.sink = sink
        self.consolidate_mode = 0

    def timeout_response(self, task):
        default_key = task['sha1hex']
        return dict(
            status="error-timeout",
            error_msg="internal GROBID worker timeout",
            source=task,
            key=default_key,
        )

    def process(self, record, key=None):
        default_key = record['sha1hex']

        fetch_result = self.fetch_blob(record)
        if fetch_result['status'] != 'success':
            return fetch_result
        blob = fetch_result['blob']

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
        self.consolidate_mode = 0

    def process(self, blob, key=None):
        if not blob:
            return None
        result = self.grobid_client.process_fulltext(blob, consolidate_mode=self.consolidate_mode)
        result['file_meta'] = gen_file_metadata(blob)
        result['key'] = result['file_meta']['sha1hex']
        return result

