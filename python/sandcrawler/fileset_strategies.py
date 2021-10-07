
import os
import sys
import json
import gzip
import time
import shutil
from collections import namedtuple
from typing import Optional, Tuple, Any, Dict, List

import internetarchive

from sandcrawler.html_metadata import BiblioMetadata
from sandcrawler.ia import ResourceResult, WaybackClient, SavePageNowClient, fix_transfer_encoding
from sandcrawler.fileset_types import IngestStrategy, FilesetManifestFile, DatasetPlatformItem, ArchiveStrategyResult
from sandcrawler.misc import gen_file_metadata, gen_file_metadata_path


class FilesetIngestStrategy():

    def __init__(self):
        #self.ingest_strategy = 'unknown'
        pass

    def check_existing(self, item: DatasetPlatformItem) -> Optional[ArchiveStrategyResult]:
        raise NotImplementedError()

    def process(self, item: DatasetPlatformItem) -> ArchiveStrategyResult:
        raise NotImplementedError()


class ArchiveorgFilesetStrategy(FilesetIngestStrategy):

    def __init__(self, **kwargs):
        self.ingest_strategy = IngestStrategy.ArchiveorgFileset

        # XXX: enable cleanup when confident (eg, safe path parsing)
        self.skip_cleanup_local_files = kwargs.get('skip_cleanup_local_files', True)
        self.working_dir = os.environ.get('SANDCRAWLER_WORKING_DIR', '/tmp/sandcrawler/')
        try:
            os.mkdir(self.working_dir)
        except FileExistsError:
            pass

        self.ia_session = internetarchive.get_session()

    def check_existing(self, item: DatasetPlatformItem) -> Optional[ArchiveStrategyResult]:
        """
        use API to check for item with all the files in the manifest

        NOTE: this naive comparison is quadratic in number of files, aka O(N^2)
        """
        ia_item = self.ia_session.get_item(item.archiveorg_item_name)
        if not ia_item.exists:
            return False
        item_files = ia_item.get_files(on_the_fly=False)
        for wanted in item.manifest:
            found = False
            for existing in item_files:
                if existing.name == wanted.path:
                    if ((existing.sha1 and existing.sha1 == wanted.sha1) or (existing.md5 and existing.md5 == wanted.md5)) and existing.name == wanted.path and existing.size == wanted.size:
                        found = True
                        wanted.status = 'exists'
                        break
                    else:
                        wanted.status = 'mismatch-existing'
                        break
            if not found:
                print(f"  item exists ({item.archiveorg_item_name}) but didn't find at least one file: {wanted.path}", file=sys.stderr)
                return None
        return ArchiveStrategyResult(
            ingest_strategy=self.ingest_strategy,
            status='success-existing',
            manifest=item.manifest,
        )

    def process(self, item: DatasetPlatformItem) -> ArchiveStrategyResult:
        """
        May require extra context to pass along to archive.org item creation.
        """
        existing = self.check_existing(item)
        if existing:
            return existing

        if item.platform_name == 'archiveorg':
            raise ValueError("should't download archive.org into itself")

        local_dir = self.working_dir + item.archiveorg_item_name
        assert local_dir.startswith('/')
        assert local_dir.count('/') > 2
        try:
            os.mkdir(local_dir)
        except FileExistsError:
            pass

        # 1. download all files locally
        for m in item.manifest:
            # XXX: enforce safe/sane filename

            local_path = local_dir + '/' + m.path
            assert m.platform_url

            if not os.path.exists(local_path):
                print(f"  downloading {m.path}", file=sys.stderr)
                with self.ia_session.get(m.platform_url, stream=True, allow_redirects=True) as r:
                    r.raise_for_status()
                    with open(local_path + '.partial', 'wb') as f:
                        for chunk in r.iter_content(chunk_size=256*1024):
                            f.write(chunk)
                os.rename(local_path + '.partial', local_path)
                m.status = 'downloaded-local'
            else:
                m.status = 'exists-local'

            print(f"  verifying {m.path}", file=sys.stderr)
            file_meta = gen_file_metadata_path(local_path, allow_empty=True)
            assert file_meta['size_bytes'] == m.size, f"expected: {m.size} found: {file_meta['size_bytes']}"

            if m.sha1:
                assert file_meta['sha1hex'] == m.sha1
            else:
                m.sha1 = file_meta['sha1hex']

            if m.sha256:
                assert file_meta['sha256hex'] == m.sha256
            else:
                m.sha256 = file_meta['sha256hex']

            if m.md5:
                assert file_meta['md5hex'] == m.md5
            else:
                m.md5 = file_meta['md5hex']

            if m.mimetype:
                # 'magic' isn't good and parsing more detailed text file formats like text/csv
                if file_meta['mimetype'] != m.mimetype and file_meta['mimetype'] != 'text/plain':
                    # these 'tab-separated-values' from dataverse are just noise, don't log them
                    if m.mimetype != 'text/tab-separated-values':
                        print(f"  WARN: mimetype mismatch: expected {m.mimetype}, found {file_meta['mimetype']}", file=sys.stderr)
                    m.mimetype = file_meta['mimetype']
            else:
                m.mimetype = file_meta['mimetype']
            m.status = 'verified-local'

        # 2. setup archive.org item metadata
        assert item.archiveorg_item_meta['collection']
        # 3. upload all files
        item_files = []
        for m in item.manifest:
            local_path = local_dir + '/' + m.path
            item_files.append({
                'name': local_path,
                'remote_name': m.path,
            })

        print(f"  uploading all files to {item.archiveorg_item_name} under {item.archiveorg_item_meta.get('collection')}...", file=sys.stderr)
        internetarchive.upload(
            item.archiveorg_item_name,
            files=item_files,
            metadata=item.archiveorg_item_meta,
            checksum=True,
            queue_derive=False,
            verify=True,
        )

        for m in item.manifest:
            m.status = 'success'

        # 4. delete local directory
        if not self.skip_cleanup_local_files:
            shutil.rmtree(local_dir)

        result = ArchiveStrategyResult(
            ingest_strategy=self.ingest_strategy,
            status='success',
            manifest=item.manifest,
        )

        return result

class ArchiveorgFileStrategy(ArchiveorgFilesetStrategy):
    """
    ArchiveorgFilesetStrategy currently works fine with individual files. Just
    need to over-ride the ingest_strategy name.
    """

    def __init__(self):
        super().__init__()
        self.ingest_strategy = IngestStrategy.ArchiveorgFileset

class WebFilesetStrategy(FilesetIngestStrategy):

    def __init__(self, **kwargs):
        self.ingest_strategy = IngestStrategy.WebFileset
        self.wayback_client = WaybackClient()
        self.try_spn2 = True
        self.spn_client = SavePageNowClient(spn_cdx_retry_sec=kwargs.get('spn_cdx_retry_sec', 9.0))

        # XXX: this is copypasta, and also should be part of SPN client, not here
        self.spn2_simple_get_domains = [
            # direct PDF links
            "://arxiv.org/pdf/",
            "://europepmc.org/backend/ptpmcrender.fcgi",
            "://pdfs.semanticscholar.org/",
            "://res.mdpi.com/",

            # platform sites
            "://zenodo.org/",
            "://figshare.org/",
            "://springernature.figshare.com/",

            # popular simple cloud storage or direct links
            "://s3-eu-west-1.amazonaws.com/",
        ]

    def process(self, item: DatasetPlatformItem) -> ArchiveStrategyResult:
        """
        For each manifest item individually, run 'fetch_resource' and record stats, terminal_url, terminal_dt

        TODO:
        - full fetch_resource() method which can do SPN requests
        """

        for m in item.manifest:
            fetch_url = m.platform_url
            if not fetch_url:
                raise NotImplementedError("require 'platform_url' for each file when doing Web fetching")

            via = "wayback"
            resource = self.wayback_client.lookup_resource(fetch_url, m.mimetype)


            if self.try_spn2 and (resource == None or (resource and resource.status == 'no-capture')):
                via = "spn2"
                force_simple_get = 0
                for domain in self.spn2_simple_get_domains:
                    if domain in fetch_url:
                        force_simple_get = 1
                        break
                resource = self.spn_client.crawl_resource(fetch_url, self.wayback_client, force_simple_get=force_simple_get)

            print("[FETCH {:>6}] {}  {}".format(
                    via,
                    (resource and resource.status),
                    (resource and resource.terminal_url) or url),
                file=sys.stderr)

            m.terminal_url = resource.terminal_url
            m.terminal_dt = resource.terminal_dt
            m.status = resource.status

            if resource.status != 'success':
                continue
            else:
                assert resource.terminal_status_code == 200

            file_meta = gen_file_metadata(resource.body)
            file_meta, html_resource = fix_transfer_encoding(file_meta, resource)

            if file_meta['size_bytes'] != m.size or (m.md5 and m.md5 != file_meta['md5hex']) or (m.sha1 and m.sha1 != file_meta['sha1hex']):
                m.status = 'mismatch'
                continue

            m.md5 = m.md5 or file_meta['md5hex']
            m.sha1 = m.sha1 or file_meta['md5hex']
            m.sha256 = m.sha256 or file_meta['sha256hex']
            m.mimetype = m.mimetype or file_meta['mimetype']

        overall_status = "success"
        for m in item.manifest:
            if m.status != 'success':
                overall_status = m.status
                break
        if not item.manifest:
            overall_status = 'empty-manifest'

        result = ArchiveStrategyResult(
            ingest_strategy=self.ingest_strategy,
            status=overall_status,
            manifest=item.manifest,
        )
        return result

class WebFileStrategy(WebFilesetStrategy):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ingest_strategy = IngestStrategy.WebFile


FILESET_STRATEGY_HELPER_TABLE = {
    IngestStrategy.ArchiveorgFileset: ArchiveorgFilesetStrategy(),
    IngestStrategy.ArchiveorgFile: ArchiveorgFileStrategy(),
    IngestStrategy.WebFileset: WebFilesetStrategy(),
    IngestStrategy.WebFile: WebFileStrategy(),
}
