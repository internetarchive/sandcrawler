import gzip
import json
import sys
import time
import urllib.parse
from collections import namedtuple
from typing import Any, Dict, List, Optional, Tuple

import internetarchive
import requests

from sandcrawler.fileset_types import *
from sandcrawler.html_metadata import BiblioMetadata
from sandcrawler.ia import ResourceResult


class FilesetPlatformHelper():
    def __init__(self):
        self.platform_name = 'unknown'

    def match_request(self, request: dict, resource: Optional[ResourceResult],
                      html_biblio: Optional[BiblioMetadata]) -> bool:
        """
        Does this request look like it matches this platform?
        """
        raise NotImplementedError()

    def process_request(self, request: dict, resource: Optional[ResourceResult],
                        html_biblio: Optional[BiblioMetadata]) -> FilesetPlatformItem:
        """
        Fetch platform-specific metadata for this request (eg, via API calls)
        """
        raise NotImplementedError()

    def chose_strategy(self, item: FilesetPlatformItem) -> IngestStrategy:
        assert item.manifest
        total_size = sum([m.size for m in item.manifest]) or 0
        largest_size = max([m.size or 0 for m in item.manifest]) or 0
        #print(f"  total_size={total_size} largest_size={largest_size}", file=sys.stderr)
        # XXX: while developing ArchiveorgFileset path
        #return IngestStrategy.ArchiveorgFileset
        if len(item.manifest) == 1:
            if total_size < 64 * 1024 * 1024:
                return IngestStrategy.WebFile
            else:
                return IngestStrategy.ArchiveorgFile
        else:
            if largest_size < 64 * 1024 * 1024 and total_size < 128 * 1024 * 1024 * 1024:
                return IngestStrategy.WebFileset
            else:
                return IngestStrategy.ArchiveorgFileset


class DataverseHelper(FilesetPlatformHelper):
    def __init__(self):
        super().__init__()
        self.platform_name = 'dataverse'
        self.session = requests.Session()

    @staticmethod
    def parse_dataverse_persistentid(pid: str) -> dict:
        """
        Parses a persistentId into 5 sections:

        - type (doi or hdl)
        - authority (eg, DOI prefix)
        - shoulder (optional, eg 'DVN')
        - dataset_id (6-digit)
        - file_id

        The returned dict always has all components, which may be 'None' if optional.

        This is possible because the dataverse software only supports a handful
        of configurations and persistend identifier types.

        If there is an error parsing, raises a ValueError
        """
        id_type = None
        if pid.startswith('doi:10.'):
            id_type = 'doi'
            pid = pid[4:]
        elif pid.startswith('hdl:'):
            id_type = 'hdl'
            pid = pid[4:]
        else:
            raise ValueError(f"unknown dataverse persistentId format: {pid}")

        comp = pid.split('/')
        if len(comp) < 2:
            raise ValueError(f"unknown dataverse persistentId format: {pid}")

        authority = comp[0]
        shoulder = None
        dataset_id = None
        file_id = None
        if len(comp[1]) != 6 and len(comp) == 3:
            shoulder = comp[1]
            dataset_id = comp[2]
        elif len(comp[1]) != 6 and len(comp) == 4:
            shoulder = comp[1]
            dataset_id = comp[2]
            file_id = comp[3]
        elif len(comp[1]) == 6 and len(comp) == 2:
            dataset_id = comp[1]
        elif len(comp[1]) == 6 and len(comp) == 3:
            dataset_id = comp[1]
            file_id = comp[2]
        else:
            raise ValueError(f"unknown dataverse persistentId format: {pid}")

        if len(dataset_id) != 6:
            raise ValueError(f"expected a 6-digit dataverse dataset id: {dataset_id}")
        if file_id and len(file_id) != 6:
            raise ValueError(f"expected a 6-digit dataverse file id: {file_id}")

        return {
            "type": id_type,
            "authority": authority,
            "shoulder": shoulder,
            "dataset_id": dataset_id,
            "file_id": file_id,
        }

    def match_request(self, request: dict, resource: Optional[ResourceResult],
                      html_biblio: Optional[BiblioMetadata]) -> bool:
        if resource and resource.terminal_url:
            url = resource.terminal_url
        else:
            url = request['base_url']

        # TODO: could also do HTML platform detection or something?

        components = urllib.parse.urlparse(url)
        platform_domain = components.netloc.split(':')[0].lower()
        params = urllib.parse.parse_qs(components.query)
        id_param = params.get('persistentId')
        if not id_param:
            return False
        platform_id = id_param[0]

        try:
            parsed = self.parse_dataverse_persistentid(platform_id)
        except ValueError:
            return False

        return True

    def process_request(self, request: dict, resource: Optional[ResourceResult],
                        html_biblio: Optional[BiblioMetadata]) -> FilesetPlatformItem:
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
        id_param = params.get('persistentId')
        if not (id_param and id_param[0]):
            raise PlatformScopeError("Expected a Dataverse persistentId in URL")
        platform_id = id_param[0]
        version_param = params.get('version')
        dataset_version = None
        if version_param:
            dataset_version = version_param[0]

        try:
            parsed_id = self.parse_dataverse_persistentid(platform_id)
        except ValueError:
            raise PlatformScopeError(f"not actually in scope")

        if parsed_id['file_id']:
            # XXX: maybe we could support this?
            raise PlatformScopeError(
                f"only entire dataverse datasets can be archived with this tool")

        # 1b. if we didn't get a version number from URL, fetch it from API
        if not dataset_version:
            resp = self.session.get(
                f"https://{platform_domain}/api/datasets/:persistentId/?persistentId={platform_id}"
            )
            resp.raise_for_status()
            obj = resp.json()
            obj_latest = obj['data']['latestVersion']
            dataset_version = f"{obj_latest['versionNumber']}.{obj_latest['versionMinorNumber']}"

        # 2. API fetch
        resp = self.session.get(
            f"https://{platform_domain}/api/datasets/:persistentId/?persistentId={platform_id}&version={dataset_version}"
        )
        resp.raise_for_status()
        obj = resp.json()

        obj_latest = obj['data']['latestVersion']
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
            manifest.append(
                FilesetManifestFile(
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
            source=
            f"https://{platform_domain}/dataset.xhtml?persistentId={platform_id}&version={dataset_version}",
        )
        if platform_id.startswith('doi:10.'):
            archiveorg_item_meta['doi'] = platform_id.replace('doi:', '')
        for block in obj_latest['metadataBlocks']['citation']['fields']:
            if block['typeName'] == 'title':
                archiveorg_item_meta['title'] = block['value']
            elif block['typeName'] == 'depositor':
                archiveorg_item_meta['creator'] = block['value']
            elif block['typeName'] == 'dsDescription':
                archiveorg_item_meta['description'] = block['value'][0]['dsDescriptionValue'][
                    'value']

        archiveorg_item_meta['description'] = archiveorg_item_meta.get('description', '')
        if obj_latest.get('termsOfUse'):
            archiveorg_item_meta['description'] += '\n<br>\n' + obj_latest['termsOfUse']

        return FilesetPlatformItem(
            platform_name=self.platform_name,
            platform_status='success',
            manifest=manifest,
            platform_domain=platform_domain,
            platform_id=platform_id,
            archiveorg_item_name=archiveorg_item_name,
            archiveorg_item_meta=archiveorg_item_meta,
            web_bundle_url=
            f"https://{platform_domain}/api/access/dataset/:persistentId/?persistentId={platform_id}&format=original",
            # TODO: web_base_url= (for GWB downloading, in lieu of platform_url on individual files)
            extra=dict(version=dataset_version),
        )


def test_parse_dataverse_persistentid():

    valid = {
        "doi:10.25625/LL6WXZ": {
            "type": "doi",
            "authority": "10.25625",
            "shoulder": None,
            "dataset_id": "LL6WXZ",
            "file_id": None,
        },
        "doi:10.25625/LL6WXZ": {
            "type": "doi",
            "authority": "10.25625",
            "shoulder": None,
            "dataset_id": "LL6WXZ",
            "file_id": None,
        },
        "doi:10.5072/FK2/J8SJZB": {
            "type": "doi",
            "authority": "10.5072",
            "shoulder": "FK2",
            "dataset_id": "J8SJZB",
            "file_id": None,
        },
        "doi:10.5072/FK2/J8SJZB/LL6WXZ": {
            "type": "doi",
            "authority": "10.5072",
            "shoulder": "FK2",
            "dataset_id": "J8SJZB",
            "file_id": "LL6WXZ",
        },
        "hdl:20.500.12690/RIN/IDDOAH/BTNH25": {
            "type": "hdl",
            "authority": "20.500.12690",
            "shoulder": "RIN",
            "dataset_id": "IDDOAH",
            "file_id": "BTNH25",
        },
        "doi:10.7910/DVN/6HPRIG": {
            "type": "doi",
            "authority": "10.7910",
            "shoulder": "DVN",
            "dataset_id": "6HPRIG",
            "file_id": None,
        },
    }

    invalid = [
        #"doi:10.5072/FK2/J8SJZB/LL6WXZ",
        "doi:10.25625/abcd",
        "other:10.25625/LL6WXZ",
        "10.25625/LL6WXZ",
        "doi:10.5072/FK2/J8SJZB/LL6WXZv123",
    ]

    for pid, val in valid.items():
        assert DataverseHelper.parse_dataverse_persistentid(pid) == val

    for pid in invalid:
        try:
            DataverseHelper.parse_dataverse_persistentid(pid)
            assert False, "should not get here"
        except ValueError:
            pass


class FigshareHelper(FilesetPlatformHelper):
    def __init__(self):
        super().__init__()
        self.platform_name = 'figshare'
        self.session = requests.Session()

    @staticmethod
    def parse_figshare_url_path(path: str) -> Tuple[str, Optional[str]]:
        """
        Tries to parse a figshare URL into ID number and (optional) version number.

        Returns a two-element tuple; version number will be None if not found

        Raises a ValueError if not a figshare URL
        """
        # eg: /articles/Optimized_protocol_to_isolate_high_quality_genomic_DNA_from_different_tissues_of_a_palm_species/8987858/1
        #     /articles/dataset/STable_1_U-Pb_geochronologic_analyses_on_samples_xls/12127176/4

        comp = path.split('/')
        if len(comp) < 4 or comp[1] != 'articles':
            raise ValueError(f"not a figshare URL: {path}")

        comp = comp[2:]
        if comp[0] in [
                'dataset',
        ]:
            comp = comp[1:]

        if len(comp) == 3 and comp[1].isdigit() and comp[2].isdigit():
            return (comp[1], comp[2])
        elif len(comp) == 2 and comp[1].isdigit():
            return (comp[1], None)
        else:
            raise ValueError(f"couldn't find figshare identiier: {path}")

    def match_request(self, request: dict, resource: Optional[ResourceResult],
                      html_biblio: Optional[BiblioMetadata]) -> bool:

        if resource and resource.terminal_url:
            url = resource.terminal_url
        else:
            url = request['base_url']

        components = urllib.parse.urlparse(url)
        platform_domain = components.netloc.split(':')[0].lower()

        # only work with full, versioned figshare.com URLs
        if not 'figshare.com' in platform_domain:
            return False

        try:
            parsed = self.parse_figshare_url_path(components.path)
        except ValueError:
            return False

        # has file component
        if parsed[0] and parsed[1]:
            return True

        return False

    def process_request(self, request: dict, resource: Optional[ResourceResult],
                        html_biblio: Optional[BiblioMetadata]) -> FilesetPlatformItem:
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

        (platform_id, dataset_version) = self.parse_figshare_url_path(components.path)
        assert platform_id.isdigit(), f"expected numeric: {platform_id}"
        assert dataset_version and dataset_version.isdigit(
        ), f"expected numeric: {dataset_version}"

        # 1b. if we didn't get a version number from URL, fetch it from API
        # TODO: implement this code path

        # 2. API fetch
        resp = self.session.get(
            f"https://api.figshare.com/v2/articles/{platform_id}/versions/{dataset_version}")
        resp.raise_for_status()
        obj = resp.json()

        figshare_type = obj['defined_type_name']

        if not obj['is_public']:
            raise PlatformRestrictedError(f'record not public: {platform_id} {dataset_version}')
        if obj['is_embargoed']:
            raise PlatformRestrictedError(
                f'record is embargoed: {obj.get("embargo_title")} ({platform_id} {dataset_version})'
            )

        manifest = []
        for row in obj['files']:
            manifest.append(
                FilesetManifestFile(
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

        return FilesetPlatformItem(
            platform_name=self.platform_name,
            platform_status='success',
            manifest=manifest,
            platform_domain=platform_domain,
            platform_id=platform_id,
            archiveorg_item_name=archiveorg_item_name,
            archiveorg_item_meta=archiveorg_item_meta,
            web_bundle_url=
            f"https://ndownloader.figshare.com/articles/{platform_id}/versions/{dataset_version}",
            # TODO: web_base_url= (for GWB downloading, in lieu of platform_url on individual files)
            extra=dict(version=dataset_version),
        )


def test_parse_figshare_url_path():

    valid = {
        "/articles/Optimized_protocol_to_isolate_high_quality_genomic_DNA_from_different_tissues_of_a_palm_species/8987858/1":
            ("8987858", "1"),
        "/articles/Optimized_protocol_to_isolate_high_quality_genomic_DNA_from_different_tissues_of_a_palm_species/8987858":
            ("8987858", None),
        "/articles/CIBERSORT_p-value_0_05/8217188/1": ("8217188", "1"),
        "/articles/dataset/STable_1_U-Pb_geochronologic_analyses_on_samples_xls/12127176/4":
            ("12127176", "4"),
    }

    invalid = [
        "/articles/Optimized_protocol_to_isolate_high_quality_genomic_DNA_from_different_tissues_of_a_palm_species",
    ]

    for path, val in valid.items():
        assert FigshareHelper.parse_figshare_url_path(path) == val

    for path in invalid:
        try:
            FigshareHelper.parse_figshare_url_path(path)
            assert False, "should not get here"
        except ValueError:
            pass


class ZenodoHelper(FilesetPlatformHelper):
    def __init__(self):
        super().__init__()
        self.platform_name = 'zenodo'
        self.session = requests.Session()

    def match_request(self, request: dict, resource: Optional[ResourceResult],
                      html_biblio: Optional[BiblioMetadata]) -> bool:

        if resource and resource.terminal_url:
            url = resource.terminal_url
        else:
            url = request['base_url']

        components = urllib.parse.urlparse(url)
        platform_domain = components.netloc.split(':')[0].lower()
        if platform_domain == 'zenodo.org' and '/record/' in components.path:
            return True
        return False

    def process_request(self, request: dict, resource: Optional[ResourceResult],
                        html_biblio: Optional[BiblioMetadata]) -> FilesetPlatformItem:
        """
        Fetch platform-specific metadata for this request (eg, via API calls)
        """

        if resource and resource.terminal_url:
            url = resource.terminal_url
        else:
            url = request['base_url']

        # XXX: also look in base_url and resource-non-terminal for ident? to
        # check for work-level redirects

        # 1. extract identifier from URL
        # eg: https://zenodo.org/record/5230255
        components = urllib.parse.urlparse(url)
        platform_domain = components.netloc.split(':')[0].lower()
        if len(components.path.split('/')) < 2:
            raise PlatformScopeError("Expected a complete, versioned figshare URL")

        platform_id = components.path.split('/')[2]
        assert platform_id.isdigit(), f"expected numeric: {platform_id}"

        if not 'zenodo.org' in platform_domain:
            raise PlatformScopeError(f"unexpected zenodo.org domain: {platform_domain}")

        # 2. API fetch
        resp = self.session.get(f"https://zenodo.org/api/records/{platform_id}")
        if resp.status_code == 410:
            raise PlatformRestrictedError('record deleted')
        resp.raise_for_status()
        obj = resp.json()

        assert obj['id'] == int(platform_id)
        work_id = obj['conceptrecid']
        if work_id == obj['id']:
            raise PlatformScopeError(
                "got a work-level zenodo record, not a versioned record: {work_id}")

        zenodo_type = obj['metadata']['resource_type']['type']

        if obj['metadata']['access_right'] != 'open':
            raise PlatformRestrictedError(
                "not publicly available ({obj['metadata']['access_right']}): {platform_domain} {platform_id}"
            )

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

        return FilesetPlatformItem(
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


class ArchiveOrgHelper(FilesetPlatformHelper):

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
        'MP3': 'audio/mpeg',  # .mp3
        'MP4': 'video/mp4',  # .mp4
        'MPEG': 'video/mpeg',  # .mpeg
        'JPEG': 'image/jpeg',
        'GIF': 'image/gif',
        'PNG': 'image/png',
        'TIFF': 'image/tiff',
        'Unknown': None,
    }

    def __init__(self):
        super().__init__()
        self.platform_name = 'archiveorg'
        self.session = internetarchive.get_session()

    @staticmethod
    def want_item_file(f: internetarchive.File, item_name: str) -> bool:
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
            for suffix in [
                    '_academictorrents.torrent', '_academictorrents_torrent.txt', '.bib'
            ]:
                if f.name == item_name + suffix:
                    return False
        return True

    def match_request(self, request: dict, resource: Optional[ResourceResult],
                      html_biblio: Optional[BiblioMetadata]) -> bool:

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

    def process_request(self, request: dict, resource: Optional[ResourceResult],
                        html_biblio: Optional[BiblioMetadata]) -> FilesetPlatformItem:
        """
        Fetch platform-specific metadata for this request (eg, via API calls)
        """

        base_url_split = request['base_url'].split('/')
        #print(base_url_split, file=sys.stderr)
        assert len(base_url_split) in [5, 6]
        assert base_url_split[0] in ['http:', 'https:']
        assert base_url_split[2] == 'archive.org'
        assert base_url_split[3] in ['details', 'download']
        item_name = base_url_split[4]
        if len(base_url_split) == 6 and base_url_split[5]:
            raise PlatformScopeError(
                "got an archive.org file path, not download/details page; individual files not handled yet"
            )

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

        return FilesetPlatformItem(
            platform_name=self.platform_name,
            platform_status='success',
            manifest=manifest,
            platform_domain='archive.org',
            platform_id=item_name,
            archiveorg_item_name=item_name,
            archiveorg_meta=dict(collection=item_collection),
        )

    def chose_strategy(self, item: FilesetPlatformItem) -> IngestStrategy:
        """
        Don't use default strategy picker; we are always doing an 'existing' in this case.
        """
        assert item.manifest is not None
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
