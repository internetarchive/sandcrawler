
"""
cdx
- read raw CDX, filter
- push to SQL table

ingest-file-result
- read JSON format (batch)
- cdx SQL push batch (on conflict skip)
- file_meta SQL push batch (on conflict update)
- ingest request push batch (on conflict skip)
- ingest result push batch (on conflict update)

grobid
- reads JSON format (batch)
- grobid2json
- minio push (one-by-one)
- grobid SQL push batch (on conflict update)
- file_meta SQL push batch (on conflict update)
"""

from sandcrawler.workers import SandcrawlerWorker
from sandcrawler.db import SandcrawlerPostgresClient
from sandcrawler.minio import SandcrawlerMinioClient
from sandcrawler.grobid import GrobidClient


class PersistCdxWorker(SandcrawlerWorker):

    def __init__(self, db_url, **kwargs):
        super().__init__()
        self.db = SandcrawlerPostgresClient(db_url)
        self.cur = self.db.conn.cursor()

    def process(self, record):
        """
        Only do batches (as transactions)
        """
        raise NotImplementedError

    def push_batch(self, batch):
        self.counts['total'] += len(batch)
        resp = self.db.insert_cdx(self.cur, batch)
        self.counts['insert-cdx'] += resp
        self.db.commit()
        return []

class PersistIngestFileResultWorker(SandcrawlerWorker):

    def __init__(self, db_url, **kwargs):
        super().__init__()
        self.db = SandcrawlerPostgresClient(db_url)
        self.cur = self.db.conn.cursor()

    def process(self, record):
        """
        Only do batches (as transactions)
        """
        raise NotImplementedError

    def request_to_row(self, raw):
        """
        Converts ingest-request JSON schema (eg, from Kafka) to SQL ingest_request schema

        if there is a problem with conversion, return None
        """
        # backwards compat hacks; transform request to look like current schema
        if raw.get('ingest_type') == 'file':
            raw['ingest_type'] = 'pdf'
        if (not raw.get('link_source')
                and raw.get('base_url')
                and raw.get('ext_ids', {}).get('doi')
                and raw['base_url'] == "https://doi.org/{}".format(raw['ext_ids']['doi'])):
            # set link_source(_id) for old ingest requests
            raw['link_source'] = 'doi'
            raw['link_source_id'] = raw['ext_ids']['doi']
        if (not raw.get('link_source')
                and raw.get('ingest_request_source', '').startswith('savepapernow')
                and raw.get('fatcat', {}).get('release_ident')):
            # set link_source(_id) for old ingest requests
            raw['link_source'] = 'spn'
            raw['link_source_id'] = raw['fatcat']['release_ident']

        for k in ('ingest_type', 'base_url', 'link_source', 'link_source_id'):
            if not k in raw:
                self.counts['skip-fields'] += 1
                return None
        if raw['ingest_type'] not in ('pdf', 'xml'):
            print(raw['ingest_type'])
            self.counts['skip-ingest-type'] += 1
            return None
        request = {
            'ingest_type': raw['ingest_type'],
            'base_url': raw['base_url'],
            'link_source': raw['link_source'],
            'link_source_id': raw['link_source_id'],
            'request': {},
        }
        # extra/optional fields
        if raw.get('release_stage'):
            request['release_stage'] = raw['release_stage']
        if raw.get('fatcat', {}).get('release_ident'):
            request['request']['release_ident'] = raw['fatcat']['release_ident']
        for k in ('ext_ids', 'edit_extra'):
            if raw.get(k):
                request['request'][k] = raw[k]
        # if this dict is empty, trim it to save DB space
        if not request['request']:
            request['request'] = None
        return request
            

    def file_result_to_row(self, raw):
        """
        Converts ingest-result JSON schema (eg, from Kafka) to SQL ingest_file_result schema

        if there is a problem with conversion, return None and set skip count
        """
        for k in ('request', 'hit', 'status'):
            if not k in raw:
                self.counts['skip-fields'] += 1
                return None
        if not 'base_url' in raw['request']:
            self.counts['skip-fields'] += 1
            return None
        ingest_type = raw['request'].get('ingest_type')
        if ingest_type == 'file':
            ingest_type = 'pdf'
        if ingest_type not in ('pdf', 'xml'):
            self.counts['skip-ingest-type'] += 1
            return None
        result = {
            'ingest_type': ingest_type,
            'base_url': raw['request']['base_url'],
            'hit': raw['hit'],
            'status': raw['status'],
        }
        terminal = raw.get('terminal')
        if terminal:
            result['terminal_url'] = terminal['url']
            if terminal.get('status_code') == None and terminal.get('http_status'):
                terminal['status_code'] = terminal['http_status']
            result['terminal_status_code'] = int(terminal['status_code'])
            if raw.get('file_meta'):
                result['terminal_sha1hex'] = raw['file_meta']['sha1hex']
            if raw.get('cdx') and raw['cdx']['url'] == terminal['url']:
                result['terminal_dt'] = raw['cdx']['datetime']
        return result

    def push_batch(self, batch):
        self.counts['total'] += len(batch)

        if not batch:
            return []

        results = [self.file_result_to_row(raw) for raw in batch]
        results = [r for r in results if r]
        requests = [self.request_to_row(raw['request']) for raw in batch if raw.get('request')]
        requests = [r for r in requests if r]

        if requests:
            resp = self.db.insert_ingest_request(self.cur, requests)
            self.counts['insert-requests'] += resp
        if results:
            resp = self.db.insert_ingest_file_result(self.cur, results, on_conflict="update")
            self.counts['insert-results'] += resp

        # these schemas match, so can just pass through
        # TODO: need to include warc_path etc in ingest-result
        cdx_batch = [r['cdx'] for r in batch if r.get('hit') and r.get('cdx') and r['cdx'].get('warc_path')]
        if cdx_batch:
            resp = self.db.insert_cdx(self.cur, cdx_batch)
            self.counts['insert-cdx'] += resp
        file_meta_batch = [r['file_meta'] for r in batch if r.get('hit') and r.get('file_meta')]
        if file_meta_batch:
            resp = self.db.insert_file_meta(self.cur, file_meta_batch)
            self.counts['insert-file_meta'] += resp

        self.db.commit()
        return []


class PersistGrobidWorker(SandcrawlerWorker):

    def __init__(self, db_url, **kwargs):
        super().__init__()
        self.db = SandcrawlerPostgresClient(db_url)
        self.cur = self.db.conn.cursor()
        self.grobid = GrobidClient()

    def process(self, record):
        """
        Only do batches (as transactions)
        """
        raise NotImplementedError

    def push_batch(self, batch):
        self.counts['total'] += len(batch)

        # enhance with teixml2json metadata, if available
        for r in batch:
            if r['status_code'] != 200 or not r.get('tei_xml'):
                continue
            metadata = self.grobid.metadata(r)
            if not metadata:
                continue
            for k in ('fatcat_release', 'grobid_version'):
                r[k] = metadata.pop(k, None)
            if r.get('fatcat_release'):
                r['fatcat_release'] = r['fatcat_release'].replace('release_', '')
            if metadata.get('grobid_timestamp'):
                r['updated'] = metadata['grobid_timestamp']
            r['metadata'] = metadata

        grobid_batch = [r['grobid'] for r in batch if r.get('grobid')]
        resp = self.db.insert_grobid(self.cur, batch, on_conflict="update")
        self.counts['insert-grobid'] += resp

        file_meta_batch = [r['file_meta'] for r in batch if r.get('file_meta')]
        resp = self.db.insert_file_meta(self.cur, file_meta_batch)
        self.counts['insert-file-meta'] += resp

        # TODO: minio

        self.db.commit()
        return []

