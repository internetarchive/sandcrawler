
import sys
import json
import gzip
import time
import urllib.parse
from collections import namedtuple
from typing import Optional, Tuple, Any, Dict, List

import requests
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

    def chose_strategy(self, item: DatasetPlatformItem) -> IngestStrategy:
        assert item.manifest
        total_size = sum([m.size for m in item.manifest])
        largest_size = max([m.size for m in item.manifest])
        #print(f"  total_size={total_size} largest_size={largest_size}", file=sys.stderr)
        # XXX: while developing ArchiveorgFileset path
        #return IngestStrategy.ArchiveorgFileset
        if len(item.manifest) == 1:
            if total_size < 64*1024*1024: 
                return IngestStrategy.WebFile
            else:
                return IngestStrategy.ArchiveorgFile
        else:
            if largest_size < 64*1024*1024 and total_size < 128*1024*1024*1024:
                return IngestStrategy.WebFileset
            else:
                return IngestStrategy.ArchiveorgFileset


class DataverseHelper(DatasetPlatformHelper):

    def __init__(self):
        self.platform_name = 'dataverse'
        self.session = requests.Session()
        self.dataverse_domain_allowlist = [
            'dataverse.harvard.edu',
            'data.lipi.go.id',
        ]

    def match_request(self, request: dict , resource: Optional[ResourceResult], html_biblio: Optional[BiblioMetadata]) -> bool:
        if resource and resource.terminal_url:
            url = resource.terminal_url
        else:
            url = request['base_url']

        components = urllib.parse.urlparse(url)
        platform_domain = components.netloc.split(':')[0].lower()
        params = urllib.parse.parse_qs(components.query)
        platform_id = params.get('persistentId')

        if not platform_domain in self.dataverse_domain_allowlist:
            return False
        if not platform_id:
            return False

        if html_biblio and 'dataverse' in html_biblio.publisher.lower():
            return True
        return False

    def process_request(self, request: dict, resource: Optional[ResourceResult], html_biblio: Optional[BiblioMetadata]) -> DatasetPlatformItem:
        """
        Fetch platform-specific metadata for this request (eg, via API calls)


        HTTP GET https://demo.dataverse.org/api/datasets/export?exporter=dataverse_json&persistentId=doi:10.5072/FK2/J8SJZB
        """

        if resource and resource.terminal_url:
            url = resource.terminal_url
        else:
            url = request['base_url']

        # 1. extract domain, PID, and version from URL
        components = urllib.parse.urlparse(url)
        platform_domain = components.netloc.split(':')[0].lower()
        params = urllib.parse.parse_qs(components.query)
        dataset_version = params.get('version')
        platform_id = params.get('persistentId')
        if not (platform_id and platform_id[0]):
            raise ValueError("Expected a Dataverse persistentId in URL")
        else:
            platform_id = platform_id[0]

        if not platform_domain in self.dataverse_domain_allowlist:
            raise ValueError(f"unexpected dataverse domain: {platform_domain}")

        # for both handle (hdl:) and DOI (doi:) identifiers, the norm is for
        # dataverse persistetId is to be structured like:
        # <prefix> / <shoulder> / <dataset-id> / <file-id>
        if not (platform_id.startswith('doi:10.') or platform_id.startswith('hdl:')):
            raise NotImplementedError(f"unsupported dataverse persistentId format: {platform_id}")
        dataverse_type = None
        if platform_id.count('/') == 2:
            dataverse_type = 'dataset'
        elif platform_id.count('/') == 3:
            dataverse_type = 'file'
        else:
            raise NotImplementedError(f"unsupported dataverse persistentId format: {platform_id}")

        if dataverse_type != 'dataset':
            # XXX
            raise NotImplementedError(f"only entire dataverse datasets can be archived with this tool")

        # 1b. if we didn't get a version number from URL, fetch it from API
        if not dataset_version:
            obj = self.session.get(f"https://{platform_domain}/api/datasets/:persistentId/?persistentId={platform_id}").json()
            obj_latest = obj['data']['latestVersion']
            dataset_version = f"{obj_latest['versionNumber']}.{obj_latest['versionMinorNumber']}"

        # 2. API fetch
        obj = self.session.get(f"https://{platform_domain}/api/datasets/:persistentId/?persistentId={platform_id}&version={dataset_version}").json()

        obj_latest= obj['data']['latestVersion']
        assert dataset_version == f"{obj_latest['versionNumber']}.{obj_latest['versionMinorNumber']}"
        assert platform_id == obj_latest['datasetPersistentId']

        manifest = []
        for row in obj_latest['files']:
            df = row['dataFile']
            df_persistent_id = df['persistentId']
            platform_url = f"https://{platform_domain}/api/access/datafile/:persistentId/?persistentId={df_persistent_id}"
            if df.get('originalFileName'):
                platform_url += '&format=original'

            extra = dict()
            # TODO: always save the version field?
            if row.get('version') != 1:
                extra['version'] = row['version']
            if 'description' in df:
                extra['description'] = df['description']
            manifest.append(FilesetManifestFile(
                path=df.get('originalFileName') or df['filename'],
                size=df.get('originalFileSize') or df['filesize'],
                md5=df['md5'],
                # NOTE: don't get: sha1, sha256
                mimetype=df['contentType'],
                platform_url=platform_url,
                extra=extra or None,
            ))

        platform_sub_id = platform_id.split('/')[-1]
        archiveorg_item_name = f"{platform_domain}-{platform_sub_id}-v{dataset_version}"
        archiveorg_item_meta = dict(
            # XXX: collection=platform_domain,
            collection="datasets",
            date=obj_latest['releaseTime'].split('T')[0],
            source=f"https://{platform_domain}/dataset.xhtml?persistentId={platform_id}&version={dataset_version}",
        )
        if platform_id.startswith('doi:10.'):
            archiveorg_item_meta['doi'] = platform_id.replace('doi:', '')
        for block in obj_latest['metadataBlocks']['citation']['fields']:
            if block['typeName'] == 'title':
                archiveorg_item_meta['title'] = block['value']
            elif block['typeName'] == 'depositor':
                archiveorg_item_meta['creator'] = block['value']
            elif block['typeName'] == 'dsDescription':
                archiveorg_item_meta['description'] = block['value'][0]['dsDescriptionValue']['value']

        archiveorg_item_meta['description'] = archiveorg_item_meta.get('description', '') + '\n<br>\n' + obj_latest['termsOfUse']

        return DatasetPlatformItem(
            platform_name=self.platform_name,
            platform_status='success',
            manifest=manifest,
            platform_domain=platform_domain,
            platform_id=platform_id,
            archiveorg_item_name=archiveorg_item_name,
            archiveorg_item_meta=archiveorg_item_meta,
            web_bundle_url=f"https://{platform_domain}/api/access/dataset/:persistentId/?persistentId={platform_id}&format=original",
            # TODO: web_base_url= (for GWB downloading, in lieu of platform_url on individual files)
            extra=dict(version=dataset_version),
        )

class FigshareHelper(DatasetPlatformHelper):

    def __init__(self):
        self.platform_name = 'figshare'
        self.session = requests.Session()

    def match_request(self, request: dict , resource: Optional[ResourceResult], html_biblio: Optional[BiblioMetadata]) -> bool:

        if resource and resource.terminal_url:
            url = resource.terminal_url
        else:
            url = request['base_url']

        components = urllib.parse.urlparse(url)
        platform_domain = components.netloc.split(':')[0].lower()
        # only work with full, versioned figshare URLs
        if 'figshare.com' in platform_domain and '/articles/' in components.path and len(components.path.split('/')) >= 6:
            return True
        return False

    def process_request(self, request: dict, resource: Optional[ResourceResult], html_biblio: Optional[BiblioMetadata]) -> DatasetPlatformItem:
        """
        Fetch platform-specific metadata for this request (eg, via API calls)
        """

        if resource and resource.terminal_url:
            url = resource.terminal_url
        else:
            url = request['base_url']

        # 1. extract domain, PID, and version from URL
        components = urllib.parse.urlparse(url)
        platform_domain = components.netloc.split(':')[0].lower()
        if len(components.path.split('/')) < 6:
            raise ValueError("Expected a complete, versioned figshare URL")

        platform_id = components.path.split('/')[4]
        dataset_version = components.path.split('/')[5]
        assert platform_id.isdigit(), f"expected numeric: {platform_id}"
        assert dataset_version.isdigit(), f"expected numeric: {dataset_version}"

        if not 'figshare' in platform_domain:
            raise ValueError(f"unexpected figshare domain: {platform_domain}")

        # 1b. if we didn't get a version number from URL, fetch it from API
        # XXX

        # 2. API fetch
        obj = self.session.get(f"https://api.figshare.com/v2/articles/{platform_id}/versions/{dataset_version}").json()

        figshare_type = obj['defined_type_name']

        manifest = []
        for row in obj['files']:
            manifest.append(FilesetManifestFile(
                path=row['name'],
                size=row['size'],
                md5=row['computed_md5'],
                # NOTE: don't get: sha1, sha256, mimetype
                platform_url=row['download_url'],
                #extra=dict(),
            ))
            assert not row.get('is_link_only')

        authors = []
        for author in obj['authors']:
            authors.append(author['full_name'])
        archiveorg_item_name = f"{platform_domain}-{platform_id}-v{dataset_version}"
        archiveorg_item_meta = dict(
            # XXX: collection=platform_domain,
            collection="datasets",
            creator=authors,
            doi=obj['doi'],
            title=obj['title'],
            date=obj['published_date'],
            source=obj['url_public_html'],
            description=obj['description'],
            license=obj['license']['url'],
            version=obj['version'],
        )

        return DatasetPlatformItem(
            platform_name=self.platform_name,
            platform_status='success',
            manifest=manifest,
            platform_domain=platform_domain,
            platform_id=platform_id,
            archiveorg_item_name=archiveorg_item_name,
            archiveorg_item_meta=archiveorg_item_meta,
            web_bundle_url=f"https://ndownloader.figshare.com/articles/{platform_id}/versions/{dataset_version}",
            # TODO: web_base_url= (for GWB downloading, in lieu of platform_url on individual files)
            extra=dict(version=dataset_version),
        )

class ZenodoHelper(DatasetPlatformHelper):

    def __init__(self):
        self.platform_name = 'zenodo'
        self.session = requests.Session()

    def match_request(self, request: dict , resource: Optional[ResourceResult], html_biblio: Optional[BiblioMetadata]) -> bool:

        if resource and resource.terminal_url:
            url = resource.terminal_url
        else:
            url = request['base_url']

        components = urllib.parse.urlparse(url)
        platform_domain = components.netloc.split(':')[0].lower()
        if platform_domain == 'zenodo.org' and '/record/' in components.path:
            return True
        return False

    def process_request(self, request: dict, resource: Optional[ResourceResult], html_biblio: Optional[BiblioMetadata]) -> DatasetPlatformItem:
        """
        Fetch platform-specific metadata for this request (eg, via API calls)
        """

        if resource and resource.terminal_url:
            url = resource.terminal_url
        else:
            url = request['base_url']

        # 1. extract identifier from URL
        # eg: https://zenodo.org/record/5230255
        components = urllib.parse.urlparse(url)
        platform_domain = components.netloc.split(':')[0].lower()
        if len(components.path.split('/')) < 2:
            raise ValueError("Expected a complete, versioned figshare URL")

        platform_id = components.path.split('/')[2]
        assert platform_id.isdigit(), f"expected numeric: {platform_id}"

        if not 'zenodo.org' in platform_domain:
            raise ValueError(f"unexpected zenodo.org domain: {platform_domain}")

        # 2. API fetch
        obj = self.session.get(f"https://zenodo.org/api/records/{platform_id}").json()

        assert obj['id'] == int(platform_id)
        work_id = obj['conceptdoi']
        if work_id == obj['id']:
            raise ValueError("got a work-level zenodo record, not a versioned record: {work_id}")

        zenodo_type = obj['metadata']['resource_type']['type']

        manifest = []
        for row in obj['files']:
            mf = FilesetManifestFile(
                path=row['key'],
                size=row['size'],
                platform_url=row['links']['self'],
                #extra=dict(),
            )
            checksum = row['checksum']
            # eg: md5:35ffcab905f8224556dba76648cb7dad
            if checksum.startswith('md5:'):
                mf.md5 = checksum[4:]
            elif checksum.startswith('sha1:'):
                mf.sha1 = checksum[45]
            manifest.append(mf)

        authors = []
        for author in obj['metadata']['creators']:
            authors.append(author['name'])
        archiveorg_item_name = f"{platform_domain}-{platform_id}"
        archiveorg_item_meta = dict(
            # XXX: collection=platform_domain,
            collection="datasets",
            creator=authors,
            doi=obj['doi'],
            title=obj['metadata']['title'],
            date=obj['metadata']['publication_date'],
            source=obj['links']['html'],
            description=obj['metadata']['description'],
            license=obj['metadata']['license']['id'],
            version=obj['revision'],
            # obj['metadata']['version'] is, eg, git version tag
        )

        return DatasetPlatformItem(
            platform_name=self.platform_name,
            platform_status='success',
            manifest=manifest,
            platform_domain=platform_domain,
            platform_id=platform_id,
            archiveorg_item_name=archiveorg_item_name,
            archiveorg_item_meta=archiveorg_item_meta,
            #web_bundle_url=f"https://ndownloader.figshare.com/articles/{platform_id}/versions/{dataset_version}",
            # TODO: web_base_url= (for GWB downloading, in lieu of platform_url on individual files)
            extra=dict(version=obj['revision']),
        )


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

    def match_request(self, request: dict , resource: Optional[ResourceResult], html_biblio: Optional[BiblioMetadata]) -> bool:

        if resource and resource.terminal_url:
            url = resource.terminal_url
        else:
            url = request['base_url']
        patterns = [
            '://archive.org/details/',
            '://archive.org/download/',
        ]
        for p in patterns:
            if p in url:
                return True
        return False

    def process_request(self, request: dict, resource: Optional[ResourceResult], html_biblio: Optional[BiblioMetadata]) -> DatasetPlatformItem:
        """
        Fetch platform-specific metadata for this request (eg, via API calls)
        """

        base_url_split = request['base_url'].split('/')
        #print(base_url_split, file=sys.stderr)
        assert len(base_url_split) in [5,6]
        assert base_url_split[0] in ['http:', 'https:']
        assert base_url_split[2] == 'archive.org'
        assert base_url_split[3] in ['details', 'download']
        item_name = base_url_split[4]
        if len(base_url_split) == 6:
            assert not base_url_split[5]

        #print(f"  archiveorg processing item={item_name}", file=sys.stderr)
        item = self.session.get_item(item_name)
        item_name = item.identifier
        item_collection = item.metadata['collection']
        if type(item_collection) == list:
            item_collection = item_collection[0]
        assert item.metadata['mediatype'] not in ['collection', 'web']
        item_files = item.get_files(on_the_fly=False)
        item_files = [f for f in item_files if self.want_item_file(f, item_name)]
        manifest = []
        for f in item_files:
            assert f.name and f.sha1 and f.md5
            assert f.name is not None
            mf = FilesetManifestFile(
                path=f.name,
                size=int(f.size),
                sha1=f.sha1,
                md5=f.md5,
                mimetype=self.FORMAT_TO_MIMETYPE[f.format],
                platform_url=f"https://archive.org/download/{item_name}/{f.name}",
            )
            manifest.append(mf)

        return DatasetPlatformItem(
            platform_name=self.platform_name,
            platform_status='success',
            manifest=manifest,
            platform_domain='archive.org',
            platform_id=item_name,
            archiveorg_item_name=item_name,
            archiveorg_meta=dict(collection=item_collection),
        )

    def chose_strategy(self, item: DatasetPlatformItem) -> IngestStrategy:
        """
        Don't use default strategy picker; we are always doing an 'existing' in this case.
        """
        if len(item.manifest) == 1:
            # NOTE: code flow does not support ArchiveorgFilesetBundle for the
            # case of, eg, a single zipfile in an archive.org item
            return IngestStrategy.ArchiveorgFile
        elif len(item.manifest) >= 1:
            return IngestStrategy.ArchiveorgFileset
        else:
            raise NotImplementedError("empty dataset")


DATASET_PLATFORM_HELPER_TABLE = {
    'dataverse': DataverseHelper(),
    'figshare': FigshareHelper(),
    'zenodo': ZenodoHelper(),
    'archiveorg': ArchiveOrgHelper(),
}
