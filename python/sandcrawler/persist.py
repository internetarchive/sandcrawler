
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

import os

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
        self.counts['insert-cdx'] += resp[0]
        self.counts['update-cdx'] += resp[1]
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
                self.counts['skip-request-fields'] += 1
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
                self.counts['skip-result-fields'] += 1
                return None
        if not 'base_url' in raw['request']:
            self.counts['skip-result-fields'] += 1
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

        # need to ensure that we aren't trying to update same row multiple
        # times in same batch (!)
        results = [self.file_result_to_row(raw) for raw in batch]
        results.reverse()
        clean_results = []
        result_keys = []
        for r in results:
            if not r:
                continue
            key = (r['ingest_type'], r['base_url'])
            if key in result_keys:
                self.counts['skip-duplicate-result'] += 1
                continue
            result_keys.append(key)
            clean_results.append(r)
        results = clean_results

        requests = [self.request_to_row(raw['request']) for raw in batch if raw.get('request')]
        requests = [r for r in requests if r]

        if requests:
            resp = self.db.insert_ingest_request(self.cur, requests)
            self.counts['insert-requests'] += resp[0]
            self.counts['update-requests'] += resp[1]
        if results:
            resp = self.db.insert_ingest_file_result(self.cur, results, on_conflict="update")
            self.counts['insert-results'] += resp[0]
            self.counts['update-results'] += resp[1]

        # these schemas match, so can just pass through
        # TODO: need to include warc_path etc in ingest worker, when possible
        cdx_batch = [r['cdx'] for r in batch if r.get('hit') and r.get('cdx') and r['cdx'].get('warc_path')]
        if cdx_batch:
            resp = self.db.insert_cdx(self.cur, cdx_batch)
            self.counts['insert-cdx'] += resp[0]
            self.counts['update-cdx'] += resp[1]

        file_meta_batch = [r['file_meta'] for r in batch if r.get('hit') and r.get('file_meta')]
        if file_meta_batch:
            resp = self.db.insert_file_meta(self.cur, file_meta_batch, on_conflict="update")
            self.counts['insert-file_meta'] += resp[0]
            self.counts['update-file_meta'] += resp[1]

        self.db.commit()
        return []


class PersistGrobidWorker(SandcrawlerWorker):

    def __init__(self, db_url, **kwargs):
        super().__init__()
        self.db = SandcrawlerPostgresClient(db_url)
        self.cur = self.db.conn.cursor()
        self.grobid = GrobidClient()
        self.s3 = SandcrawlerMinioClient(
            host_url=kwargs.get('s3_url', 'localhost:9000'),
            access_key=kwargs['s3_access_key'],
            secret_key=kwargs['s3_secret_key'],
            default_bucket=kwargs['s3_bucket'],
        )
        self.s3_only = kwargs.get('s3_only', False)

    def process(self, record):
        """
        Only do batches (as transactions)
        """
        raise NotImplementedError

    def push_batch(self, batch):
        self.counts['total'] += len(batch)

        for r in batch:
            if r['status_code'] != 200 or not r.get('tei_xml'):
                self.counts['s3-skip-status'] += 1
                if r.get('error_msg'):
                    r['metadata'] = {'error_msg': r['error_msg'][:500]}
                continue

            assert len(r['key']) == 40
            resp = self.s3.put_blob(
                folder="grobid",
                blob=r['tei_xml'],
                sha1hex=r['key'],
                extension=".tei.xml",
            )
            self.counts['s3-put'] += 1

            # enhance with teixml2json metadata, if available
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

        if not self.s3_only:
            grobid_batch = [r['grobid'] for r in batch if r.get('grobid')]
            resp = self.db.insert_grobid(self.cur, batch, on_conflict="update")
            self.counts['insert-grobid'] += resp[0]
            self.counts['update-grobid'] += resp[1]

            file_meta_batch = [r['file_meta'] for r in batch if r.get('file_meta')]
            resp = self.db.insert_file_meta(self.cur, file_meta_batch, on_conflict="update")
            self.counts['insert-file-meta'] += resp[0]
            self.counts['update-file-meta'] += resp[1]

        self.db.commit()
        return []


class PersistGrobidDiskWorker(SandcrawlerWorker):
    """
    Writes blobs out to disk.

    This could be refactored into a "Sink" type with an even thinner wrapper.
    """

    def __init__(self, output_dir):
        super().__init__()
        self.output_dir = output_dir

    def _blob_path(self, sha1hex, extension=".tei.xml"):
        obj_path = "{}/{}/{}{}".format(
            sha1hex[0:2],
            sha1hex[2:4],
            sha1hex,
            extension,
        )
        return obj_path

    def process(self, record):

        if record['status_code'] != 200 or not record.get('tei_xml'):
            return False
        assert(len(record['key'])) == 40
        p = "{}/{}".format(self.output_dir, self._blob_path(record['key']))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w') as f:
            f.write(record.pop('tei_xml'))
        self.counts['written'] += 1
        return record

