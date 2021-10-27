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
import xml.etree.ElementTree
from typing import Any, Dict, List, Optional

from sandcrawler.db import SandcrawlerPostgresClient
from sandcrawler.grobid import GrobidClient
from sandcrawler.ingest_html import HtmlMetaRow
from sandcrawler.minio import SandcrawlerMinioClient
from sandcrawler.pdfextract import PdfExtractResult
from sandcrawler.workers import SandcrawlerWorker


class PersistCdxWorker(SandcrawlerWorker):
    def __init__(self, db_url: str, **kwargs):
        super().__init__()
        self.db = SandcrawlerPostgresClient(db_url)
        self.cur = self.db.conn.cursor()

    def process(self, record: Any, key: Optional[str] = None) -> Any:
        """Only do batches (as transactions)"""
        raise NotImplementedError

    def push_batch(self, batch: list) -> list:
        self.counts['total'] += len(batch)
        # filter to full CDX lines, no liveweb
        cdx_batch = [r for r in batch if r.get('warc_path') and ("/" in r['warc_path'])]
        resp = self.db.insert_cdx(self.cur, cdx_batch)
        if len(cdx_batch) < len(batch):
            self.counts['skip'] += len(batch) - len(cdx_batch)
        self.counts['insert-cdx'] += resp[0]
        self.counts['update-cdx'] += resp[1]
        self.db.commit()
        return []


class PersistIngestFileResultWorker(SandcrawlerWorker):
    def __init__(self, db_url: str, **kwargs):
        super().__init__()
        self.db = SandcrawlerPostgresClient(db_url)
        self.cur = self.db.conn.cursor()

    def process(self, record: Any, key: Optional[str] = None) -> Any:
        """Only do batches (as transactions)"""
        raise NotImplementedError

    def request_to_row(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Converts ingest-request JSON schema (eg, from Kafka) to SQL ingest_request schema

        if there is a problem with conversion, return None
        """
        # backwards compat hacks; transform request to look like current schema
        if raw.get('ingest_type') == 'file':
            raw['ingest_type'] = 'pdf'
        if (not raw.get('link_source') and raw.get('base_url')
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
        if raw['ingest_type'] not in ('pdf', 'xml', 'html'):
            self.counts['skip-ingest-type'] += 1
            return None
        request = {
            'ingest_type': raw['ingest_type'],
            'base_url': raw['base_url'],
            'link_source': raw['link_source'],
            'link_source_id': raw['link_source_id'],
            'ingest_request_source': raw.get('ingest_request_source'),
            'request': {},
        }
        # extra/optional fields
        if raw.get('release_stage'):
            request['release_stage'] = raw['release_stage']
        if raw.get('fatcat', {}).get('release_ident'):
            request['request']['release_ident'] = raw['fatcat']['release_ident']
        for k in ('ext_ids', 'edit_extra', 'rel'):
            if raw.get(k):
                request['request'][k] = raw[k]
        # if this dict is empty, trim it to save DB space
        if not request['request']:
            request['request'] = None
        return request

    def file_result_to_row(self, raw: dict) -> Optional[dict]:
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
        if ingest_type not in ('pdf', 'xml', 'html', 'component', 'src', 'dataset',
                               'dataset-file'):
            self.counts['skip-ingest-type'] += 1
            return None
        if raw['status'] in ("existing", ):
            self.counts['skip-existing'] += 1
            return None
        result = {
            'ingest_type': ingest_type,
            'base_url': raw['request']['base_url'],
            'hit': raw['hit'],
            'status': raw['status'],
        }
        terminal = raw.get('terminal')
        if terminal:
            result['terminal_url'] = terminal.get('terminal_url') or terminal.get('url')
            result['terminal_dt'] = terminal.get('terminal_dt')
            result['terminal_status_code'] = terminal.get(
                'terminal_status_code') or terminal.get('status_code') or terminal.get(
                    'http_code')
            if result['terminal_status_code']:
                result['terminal_status_code'] = int(result['terminal_status_code'])
            result['terminal_sha1hex'] = terminal.get('terminal_sha1hex')
            if len(result['terminal_url']) > 2048:
                # postgresql13 doesn't like extremely large URLs in b-tree index
                self.counts['skip-huge-url'] += 1
                return None
        return result

    def result_to_html_meta(self, record: dict) -> Optional[HtmlMetaRow]:
        html_body = record.get('html_body')
        file_meta = record.get('file_meta')
        if not (file_meta and html_body):
            return None
        return HtmlMetaRow(
            sha1hex=file_meta["sha1hex"],
            status=record.get('status'),
            scope=record.get('scope'),
            has_teixml=bool(html_body and html_body['status'] == 'success'),
            has_thumbnail=False,  # TODO
            word_count=(html_body and html_body.get('word_count')) or None,
            biblio=record.get('html_biblio'),
            resources=record.get('html_resources'),
        )

    def result_to_platform_row(self, raw: dict) -> Optional[dict]:
        """
        Converts fileset ingest-result JSON schema (eg, from Kafka) to SQL ingest_fileset_platform schema

        if there is a problem with conversion, return None and set skip count
        """
        for k in ('request', 'hit', 'status'):
            if not k in raw:
                return None
        if not 'base_url' in raw['request']:
            return None
        ingest_type = raw['request'].get('ingest_type')
        if ingest_type not in ('dataset'):
            return None
        if raw['status'] in ("existing", ):
            return None
        if not raw.get('platform_name'):
            return None
        result = {
            'ingest_type': ingest_type,
            'base_url': raw['request']['base_url'],
            'hit': raw['hit'],
            'status': raw['status'],
            'platform_name': raw.get('platform_name'),
            'platform_domain': raw.get('platform_domain'),
            'platform_id': raw.get('platform_id'),
            'ingest_strategy': raw.get('ingest_strategy'),
            'total_size': raw.get('total_size'),
            'file_count': raw.get('file_count'),
            'archiveorg_item_name': raw.get('archiveorg_item_name'),
            'archiveorg_item_bundle_path': None,
            'web_bundle_url': None,
            'web_bundle_dt': None,
            'manifest': raw.get('manifest'),
        }
        if result.get('fileset_bundle'):
            result['archiveorg_item_bundle_path'] = result['fileset_bundle'].get(
                'archiveorg_item_bundle_path')
            result['web_bundle_url'] = result['fileset_bundle'].get('terminal',
                                                                    {}).get('terminal_url')
            result['web_bundle_dt'] = result['fileset_bundle'].get('terminal',
                                                                   {}).get('terminal_dt')
        return result

    def push_batch(self, batch: List[Any]) -> List[Any]:
        self.counts['total'] += len(batch)

        if not batch:
            return []

        results_unfiltered = [self.file_result_to_row(raw) for raw in batch]
        results = [r for r in results_unfiltered if r]

        irequests_unfiltered = [
            self.request_to_row(raw['request']) for raw in batch if raw.get('request')
        ]
        irequests = [
            r for r in irequests_unfiltered if r and r['ingest_type'] != 'dataset-file'
        ]

        if irequests:
            resp = self.db.insert_ingest_request(self.cur, irequests)
            self.counts['insert-requests'] += resp[0]
            self.counts['update-requests'] += resp[1]
        if results:
            resp = self.db.insert_ingest_file_result(self.cur, results, on_conflict="update")
            self.counts['insert-results'] += resp[0]
            self.counts['update-results'] += resp[1]

        # these schemas match, so can just pass through
        cdx_batch = [r['cdx'] for r in batch if r.get('hit') and r.get('cdx')]
        revisit_cdx_batch = [
            r['revisit_cdx'] for r in batch if r.get('hit') and r.get('revisit_cdx')
        ]
        cdx_batch.extend(revisit_cdx_batch)
        # filter to full CDX lines, with full warc_paths (not liveweb)
        cdx_batch = [r for r in cdx_batch if r.get('warc_path') and ("/" in r['warc_path'])]
        if cdx_batch:
            resp = self.db.insert_cdx(self.cur, cdx_batch)
            self.counts['insert-cdx'] += resp[0]
            self.counts['update-cdx'] += resp[1]

        file_meta_batch = [r['file_meta'] for r in batch if r.get('hit') and r.get('file_meta')]
        if file_meta_batch:
            resp = self.db.insert_file_meta(self.cur, file_meta_batch, on_conflict="nothing")
            self.counts['insert-file_meta'] += resp[0]
            self.counts['update-file_meta'] += resp[1]

        html_meta_batch = [
            self.result_to_html_meta(r) for r in batch if r.get('hit') and r.get('html_body')
        ]
        if html_meta_batch:
            rows = [d.to_sql_tuple() for d in html_meta_batch if d]
            resp = self.db.insert_html_meta(self.cur, rows, on_conflict="update")
            self.counts['insert-html_meta'] += resp[0]
            self.counts['update-html_meta'] += resp[1]

        fileset_platform_batch_all = [
            self.result_to_platform_row(raw) for raw in batch if
            raw.get('request', {}).get('ingest_type') == 'dataset' and raw.get('platform_name')
        ]
        fileset_platform_batch: List[Dict] = [p for p in fileset_platform_batch_all if p]
        if fileset_platform_batch:
            resp = self.db.insert_ingest_fileset_platform(self.cur,
                                                          fileset_platform_batch,
                                                          on_conflict="update")
            self.counts['insert-fileset_platform'] += resp[0]
            self.counts['update-fileset_platform'] += resp[1]

        self.db.commit()
        return []


class PersistIngestFilesetWorker(SandcrawlerWorker):
    def __init__(self, db_url: str, **kwargs):
        super().__init__()
        self.db = SandcrawlerPostgresClient(db_url)
        self.cur = self.db.conn.cursor()

    def process(self, record: Any, key: Optional[str] = None) -> Any:
        """Only do batches (as transactions)"""
        raise NotImplementedError


class PersistIngestRequestWorker(PersistIngestFileResultWorker):
    def __init__(self, db_url: str, **kwargs):
        super().__init__(db_url=db_url)

    def process(self, record: Any, key: Optional[str] = None) -> Any:
        """Only do batches (as transactions)"""
        raise NotImplementedError

    def push_batch(self, batch: list) -> list:
        self.counts['total'] += len(batch)

        if not batch:
            return []

        irequests_all = [self.request_to_row(raw) for raw in batch]
        irequests: List[Dict] = [r for r in irequests_all if r]

        if irequests:
            resp = self.db.insert_ingest_request(self.cur, irequests)
            self.counts['insert-requests'] += resp[0]
            self.counts['update-requests'] += resp[1]

        self.db.commit()
        return []


class PersistGrobidWorker(SandcrawlerWorker):
    def __init__(self, db_url: str, **kwargs):
        super().__init__()
        self.grobid = GrobidClient()
        self.s3 = SandcrawlerMinioClient(
            host_url=kwargs.get('s3_url', 'localhost:9000'),
            access_key=kwargs['s3_access_key'],
            secret_key=kwargs['s3_secret_key'],
            default_bucket=kwargs['s3_bucket'],
        )
        self.s3_only = kwargs.get('s3_only', False)
        self.db_only = kwargs.get('db_only', False)
        assert not (self.s3_only and self.db_only), "Only one of s3_only and db_only allowed"
        if not self.s3_only:
            self.db: Optional[SandcrawlerPostgresClient] = SandcrawlerPostgresClient(db_url)
            self.cur = self.db.conn.cursor()
        else:
            self.db = None
            self.cur = None

    def process(self, record: Any, key: Optional[str] = None) -> Any:
        """Only do batches (as transactions)"""
        raise NotImplementedError

    def push_batch(self, batch: list) -> list:
        self.counts['total'] += len(batch)

        # filter out bad "missing status_code" timeout rows
        missing = [r for r in batch if not r.get('status_code')]
        if missing:
            self.counts['skip-missing-status'] += len(missing)
            batch = [r for r in batch if r.get('status_code')]

        for r in batch:
            if r['status_code'] != 200 or not r.get('tei_xml'):
                self.counts['s3-skip-status'] += 1
                if r.get('error_msg'):
                    r['metadata'] = {'error_msg': r['error_msg'][:500]}
                continue

            assert len(r['key']) == 40
            if not self.db_only:
                self.s3.put_blob(
                    folder="grobid",
                    blob=r['tei_xml'],
                    sha1hex=r['key'],
                    extension=".tei.xml",
                )
                self.counts['s3-put'] += 1

            # enhance with teixml2json metadata, if available
            try:
                metadata = self.grobid.metadata(r)
            except xml.etree.ElementTree.ParseError as xml_e:
                r['status'] = 'bad-grobid-xml'
                r['metadata'] = {'error_msg': str(xml_e)[:1024]}
                continue
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
            assert self.db and self.cur
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
    def __init__(self, output_dir: str):
        super().__init__()
        self.output_dir = output_dir

    def _blob_path(self, sha1hex: str, extension: str = ".tei.xml") -> str:
        obj_path = "{}/{}/{}{}".format(
            sha1hex[0:2],
            sha1hex[2:4],
            sha1hex,
            extension,
        )
        return obj_path

    def process(self, record: Any, key: Optional[str] = None) -> Any:

        if record.get('status_code') != 200 or not record.get('tei_xml'):
            return False
        assert (len(record['key'])) == 40
        p = "{}/{}".format(self.output_dir, self._blob_path(record['key']))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w') as f:
            f.write(record.pop('tei_xml'))
        self.counts['written'] += 1
        return record


class PersistPdfTrioWorker(SandcrawlerWorker):
    def __init__(self, db_url: str, **kwargs):
        super().__init__()
        self.db = SandcrawlerPostgresClient(db_url)
        self.cur = self.db.conn.cursor()

    def process(self, record: Any, key: Optional[str] = None) -> Any:
        """Only do batches (as transactions)"""
        raise NotImplementedError

    def push_batch(self, batch: list) -> list:
        self.counts['total'] += len(batch)

        batch = [r for r in batch if 'pdf_trio' in r and r['pdf_trio'].get('status_code')]
        for r in batch:
            # copy key (sha1hex) into sub-object
            r['pdf_trio']['key'] = r['key']
        pdftrio_batch = [r['pdf_trio'] for r in batch]
        resp = self.db.insert_pdftrio(self.cur, pdftrio_batch, on_conflict="update")
        self.counts['insert-pdftrio'] += resp[0]
        self.counts['update-pdftrio'] += resp[1]

        file_meta_batch = [
            r['file_meta'] for r in batch
            if r['pdf_trio']['status'] == "success" and r.get('file_meta')
        ]
        resp = self.db.insert_file_meta(self.cur, file_meta_batch)
        self.counts['insert-file-meta'] += resp[0]
        self.counts['update-file-meta'] += resp[1]

        self.db.commit()
        return []


class PersistPdfTextWorker(SandcrawlerWorker):
    """
    Pushes text file to blob store (S3/seaweed/minio) and PDF metadata to SQL table.

    Should keep batch sizes small.
    """
    def __init__(self, db_url: str, **kwargs):
        super().__init__()
        self.s3 = SandcrawlerMinioClient(
            host_url=kwargs.get('s3_url', 'localhost:9000'),
            access_key=kwargs['s3_access_key'],
            secret_key=kwargs['s3_secret_key'],
            default_bucket=kwargs['s3_bucket'],
        )
        self.s3_only = kwargs.get('s3_only', False)
        self.db_only = kwargs.get('db_only', False)
        assert not (self.s3_only and self.db_only), "Only one of s3_only and db_only allowed"
        if not self.s3_only:
            self.db: Optional[SandcrawlerPostgresClient] = SandcrawlerPostgresClient(db_url)
            self.cur = self.db.conn.cursor()
        else:
            self.db = None
            self.cur = None

    def process(self, record: Any, key: Optional[str] = None) -> Any:
        """Only do batches (as transactions)"""
        raise NotImplementedError

    def push_batch(self, batch: list) -> list:
        self.counts['total'] += len(batch)

        parsed_batch = []
        for r in batch:
            parsed_batch.append(PdfExtractResult.from_pdftext_dict(r))

        for r in parsed_batch:
            if r.status != 'success' or not r.text:
                self.counts['s3-skip-status'] += 1
                if r.error_msg:
                    r.metadata = {'error_msg': r.error_msg[:500]}
                continue

            assert len(r.sha1hex) == 40
            if not self.db_only:
                self.s3.put_blob(
                    folder="text",
                    blob=r.text,
                    sha1hex=r.sha1hex,
                    extension=".txt",
                )
                self.counts['s3-put'] += 1

        if not self.s3_only:
            assert self.db and self.cur
            rows = [r.to_sql_tuple() for r in parsed_batch]
            resp = self.db.insert_pdf_meta(self.cur, rows, on_conflict="update")
            self.counts['insert-pdf-meta'] += resp[0]
            self.counts['update-pdf-meta'] += resp[1]

            file_meta_batch = [r.file_meta for r in parsed_batch if r.file_meta]
            resp = self.db.insert_file_meta(self.cur, file_meta_batch, on_conflict="update")
            self.counts['insert-file-meta'] += resp[0]
            self.counts['update-file-meta'] += resp[1]

            self.db.commit()

        return []


class PersistThumbnailWorker(SandcrawlerWorker):
    """
    Pushes text file to blob store (S3/seaweed/minio) and PDF metadata to SQL
    table.

    This worker *must* be used with raw kakfa mode; thumbnails are *not*
    wrapped in JSON like most sandcrawler kafka messages.
    """
    def __init__(self, **kwargs):
        super().__init__()
        self.s3 = SandcrawlerMinioClient(
            host_url=kwargs.get('s3_url', 'localhost:9000'),
            access_key=kwargs['s3_access_key'],
            secret_key=kwargs['s3_secret_key'],
            default_bucket=kwargs['s3_bucket'],
        )
        self.s3_extension = kwargs.get('s3_extension', ".jpg")
        self.s3_folder = kwargs.get('s3_folder', "pdf")

    def process(self, record: Any, key: Optional[str] = None) -> Any:
        """
        Processing raw messages, not decoded JSON objects
        """

        assert isinstance(record, bytes)
        blob: bytes = record
        if isinstance(key, bytes):
            key = key.decode('utf-8')
        assert key is not None and len(key) == 40 and isinstance(key, str)
        assert len(blob) >= 50

        self.s3.put_blob(
            folder=self.s3_folder,
            blob=blob,
            sha1hex=key,
            extension=self.s3_extension,
        )
        self.counts['s3-put'] += 1


class GenericPersistDocWorker(SandcrawlerWorker):
    """
    Pushes blobs from Kafka to S3.

    Objects are assumed to be JSON-wrapped strings.
    """
    def __init__(self, **kwargs):
        super().__init__()
        self.s3 = SandcrawlerMinioClient(
            host_url=kwargs.get('s3_url', 'localhost:9000'),
            access_key=kwargs['s3_access_key'],
            secret_key=kwargs['s3_secret_key'],
            default_bucket=kwargs['s3_bucket'],
        )
        self.s3_extension = kwargs.get('s3_extension', ".unknown")
        self.s3_folder = kwargs.get('s3_folder', "unknown")
        self.doc_key = "unknown"

    def process(self, record: Any, key: Optional[str] = None) -> Any:

        if record.get('status') != 'success' or not record.get(self.doc_key):
            return

        assert key is not None
        if isinstance(key, bytes):
            key_str = key.decode('utf-8')
        elif isinstance(key, str):
            key_str = key
        assert len(key_str) == 40
        if 'sha1hex' in record:
            assert key_str == record['sha1hex']

        self.s3.put_blob(
            folder=self.s3_folder,
            blob=record[self.doc_key].encode('utf-8'),
            sha1hex=key_str,
            extension=self.s3_extension,
        )
        self.counts['s3-put'] += 1


class PersistXmlDocWorker(GenericPersistDocWorker):
    """
    Pushes TEI-XML file to blob store (S3/seaweed/minio). Does not talk to
    sandcrawler database (SQL).
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.s3_extension = kwargs.get('s3_extension', ".jats.xml")
        self.s3_folder = kwargs.get('s3_folder', "xml_doc")
        self.doc_key = "jats_xml"


class PersistHtmlTeiXmlWorker(GenericPersistDocWorker):
    """
    Pushes TEI-XML file to blob store (S3/seaweed/minio). Does not talk to
    sandcrawler database (SQL).
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.s3_extension = kwargs.get('s3_extension', ".tei.xml")
        self.s3_folder = kwargs.get('s3_folder', "html_body")
        self.doc_key = "tei_xml"
