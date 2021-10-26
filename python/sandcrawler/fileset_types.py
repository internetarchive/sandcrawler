from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel


class IngestStrategy(str, Enum):
    WebFile = "web-file"
    WebFileset = "web-fileset"
    WebFilesetBundled = "web-fileset-bundled"
    ArchiveorgFile = "archiveorg-file"
    ArchiveorgFileset = "archiveorg-fileset"
    ArchiveorgFilesetBundled = "archiveorg-fileset-bundled"


class FilesetManifestFile(BaseModel):
    path: str
    size: Optional[int]
    md5: Optional[str]
    sha1: Optional[str]
    sha256: Optional[str]
    mimetype: Optional[str]
    extra: Optional[Dict[str, Any]]

    status: Optional[str]
    platform_url: Optional[str]
    terminal_url: Optional[str]
    terminal_dt: Optional[str]


class FilesetPlatformItem(BaseModel):
    platform_name: str
    platform_status: str
    platform_domain: Optional[str]
    platform_id: Optional[str]
    manifest: Optional[List[FilesetManifestFile]]

    archiveorg_item_name: Optional[str]
    archiveorg_item_meta: Optional[dict]
    web_base_url: Optional[str]
    web_bundle_url: Optional[str]


class ArchiveStrategyResult(BaseModel):
    ingest_strategy: str
    status: str
    manifest: List[FilesetManifestFile]
    file_file_meta: Optional[Dict[str, Any]]
    file_resource: Optional[Any]
    bundle_file_meta: Optional[Dict[str, Any]]
    bundle_resource: Optional[Any]
    bundle_archiveorg_path: Optional[str]


class PlatformScopeError(Exception):
    """
    For incidents where platform helper discovers that the fileset/dataset is
    out-of-cope after already starting to process it.

    For example, attempting to ingest:

    - a 'latest version' record, when the platform has version-specific records
    - a single file within a dataset for a platform which has file-level identifiers
    """
    pass


class PlatformRestrictedError(Exception):
    """
    When datasets are not publicly available on a platform (yet)
    """
    pass
