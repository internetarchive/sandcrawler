
import sys
import json
import gzip
import time
from collections import namedtuple
from typing import Optional, Tuple, Any, Dict, List

import internetarchive

from sandcrawler.html_metadata import BiblioMetadata
from sandcrawler.ia import ResourceResult
from sandcrawler.fileset_types import IngestStrategy, FilesetManifestFile, DatasetPlatformItem, ArchiveStrategyResult


class FilesetIngestStrategy():

    def __init__(self):
        #self.ingest_strategy = 'unknown'
        pass

    def check_existing(self, item: DatasetPlatformItem) -> Optional[ArchiveStrategyResult]:
        raise NotImplementedError()

    def process(self, item: DatasetPlatformItem) -> ArchiveStrategyResult:
        raise NotImplementedError()


class ArchiveorgFilesetStrategy(FilesetIngestStrategy):

    def __init__(self):
        self.ingest_strategy = IngestStrategy.ArchiveorgFileset
        self.session = internetarchive.get_session()

    def check_existing(self, item: DatasetPlatformItem) -> Optional[ArchiveStrategyResult]:
        """
        use API to check for item with all the files in the manifest
        TODO: this naive comparison is quadratic in number of files, aka O(N^2)

        XXX: should this verify sha256 and/or mimetype?
        """
        ia_item = self.session.get_item(item.archiveorg_item_name)
        item_files = ia_item.get_files(on_the_fly=False)
        for wanted in item.manifest:
            found = False
            for existing in item_files:
                if existing.sha1 == wanted.sha1 and existing.name == wanted.path and existing.size == wanted.size:
                    found = True
                    break
            if not found:
                print(f"  didn't find at least one file: {wanted}", file=sys.stderr)
                return None
        return ArchiveStrategyResult(
            ingest_strategy=self.ingest_strategy,
            status='success-existing',
            manifest=item.manifest,
        )

    def process(self, item: DatasetPlatformItem) -> ArchiveStrategyResult:
        existing = self.check_existing(item)
        if existing:
            return existing
        raise NotImplementedError()

FILESET_STRATEGY_HELPER_TABLE = {
    IngestStrategy.ArchiveorgFileset: ArchiveorgFilesetStrategy(),
}
