
import sys
import json
import gzip
import time
from collections import namedtuple
from typing import Optional, Tuple, Any, Dict, List

import internetarchive

from sandcrawler.html_metadata import BiblioMetadata
from sandcrawler.ia import ResourceResult
from sandcrawler.fileset_types import *


class DatasetPlatformHelper():

    def __init__(self):
        self.platform_name = 'unknown'

    def match_request(self, request: dict , resource: Optional[ResourceResult], html_biblio: Optional[BiblioMetadata]) -> bool:
        """
        Does this request look like it matches this platform?
        """
        raise NotImplementedError()

    def process_request(self, request: dict, resource: Optional[ResourceResult], html_biblio: Optional[BiblioMetadata]) -> DatasetPlatformItem:
        """
        Fetch platform-specific metadata for this request (eg, via API calls)
        """
        raise NotImplementedError()

    def chose_strategy(self, DatasetPlatformItem) -> IngestStrategy:
        raise NotImplementedError()


class DataverseHelper(DatasetPlatformHelper):

    def __init__(self):
        self.platform_name = 'dataverse'

    def match_request(self, request: dict , resource: Optional[ResourceResult], html_biblio: Optional[BiblioMetadata]) -> bool:
        return False

    def chose_strategy(self, DatasetPlatformItem) -> IngestStrategy:
        raise NotImplementedError()


class ArchiveOrgHelper(DatasetPlatformHelper):

    FORMAT_TO_MIMETYPE = {
        'BZIP': 'application/x-bzip',
        'BZIP2': 'application/x-bzip2',
        'ZIP': 'application/zip',
        'GZIP': 'application/gzip',
        'RAR': 'application/vnd.rar',
        'TAR': 'application/x-tar',
        '7z': 'application/x-7z-compressed',

        'HTML': 'text/html',
        'Text': 'text/plain',
        'PDF': 'application/pdf',

        'CSV': 'text/csv',
        'XML': 'application/xml',
        'JSON': 'application/json',

        #'application/msword (.doc)', # .doc
        #'application/vnd.openxmlformats-officedocument.wordprocessingml.document', # .docx
        #'application/vnd.ms-excel', # .xls
        #'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', # .xlsx

        'MP3': 'audio/mpeg', # .mp3

        'MP4': 'video/mp4', # .mp4
        'MPEG': 'video/mpeg', # .mpeg

        'JPEG': 'image/jpeg',
        'GIF': 'image/gif',
        'PNG': 'image/png',
        'TIFF': 'image/tiff',

        'Unknown': None,
    }

    def __init__(self):
        self.platform_name = 'archiveorg'
        self.session = internetarchive.get_session()

    @staticmethod
    def want_item_file(f: dict, item_name: str) -> bool:
        """
        Filters IA API files
        """
        if f.source != 'original':
            return False
        for suffix in [
            '_meta.sqlite',
            '_archive.torrent',
            '_itemimage.jpg',
            '_meta.xml',
            '_thumb.png',
            '_files.xml',
        ]:
            if f.name == item_name + suffix or f.name == item_name.lower() + suffix:
                return False
        if f.name.startswith('_'):
            return False
        if item_name.startswith('academictorrents_'):
            for suffix in ['_academictorrents.torrent', '_academictorrents_torrent.txt', '.bib']:
                if f.name == item_name + suffix:
                    return False
        return True

    def parse_item_file(self, f: dict) -> FilesetManifestFile:
        """
        Takes an IA API file and turns it in to a fatcat fileset manifest file
        """
        assert f.name and f.sha1 and f.md5
        assert f.name is not None
        mf = {
            'path': f.name,
            'size': int(f.size),
            'sha1': f.sha1,
            'md5': f.md5,
        }
        # TODO: will disable this hard check eventually and replace with:
        #mimetype = FORMAT_TO_MIMETYPE.get(f.format)
        mimetype = self.FORMAT_TO_MIMETYPE[f.format]
        if mimetype:
            mf['extra'] = dict(mimetype=mimetype)
        return mf


    def match_request(self, request: dict , resource: Optional[ResourceResult], html_biblio: Optional[BiblioMetadata]) -> bool:
        patterns = [
            '://archive.org/details/',
            '://archive.org/download/',
        ]
        for p in patterns:
            if p in request['base_url']:
                return True
        return False

    def process_request(self, request: dict, resource: Optional[ResourceResult], html_biblio: Optional[BiblioMetadata]) -> DatasetPlatformItem:
        """
        Fetch platform-specific metadata for this request (eg, via API calls)

        XXX: add platform_url (for direct download)
        """

        base_url_split = request['base_url'].split('/')
        #print(base_url_split, file=sys.stderr)
        assert len(base_url_split) == 5
        assert base_url_split[0] in ['http:', 'https:']
        assert base_url_split[2] == 'archive.org'
        assert base_url_split[3] in ['details', 'download']
        item_name = base_url_split[4]

        print(f"  archiveorg processing item={item_name}", file=sys.stderr)
        item = self.session.get_item(item_name)
        item_name = item.identifier
        item_collection = item.metadata['collection']
        if type(item_collection) == list:
            item_collection = item_collection[0]
        assert item.metadata['mediatype'] not in ['collection', 'web']
        item_files = item.get_files(on_the_fly=False)
        manifest = [self.parse_item_file(f) for f in item_files if self.want_item_file(f, item_name)]

        return DatasetPlatformItem(
            platform_name=self.platform_name,
            platform_status='success',
            manifest=manifest,
            platform_domain='archive.org',
            platform_id=item_name,
            archiveorg_item_name=item_name,
            archiveorg_collection=item_collection,
        )

    def chose_strategy(self, item: DatasetPlatformItem) -> IngestStrategy:
        if len(item.manifest) == 1:
            # NOTE: code flow does not support ArchiveorgFilesetBundle for the
            # case of, eg, a single zipfile in an archive.org item
            return IngestStrategy.ArchiveorgFile
        elif len(item.manifest) >= 1:
            return IngestStrategy.ArchiveorgFileset
        else:
            raise NotImplementedError()


DATASET_PLATFORM_HELPER_TABLE = {
    'dataverse': DataverseHelper(),
    'archiveorg': ArchiveOrgHelper(),
}
