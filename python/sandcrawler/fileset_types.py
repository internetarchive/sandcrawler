
from enum import Enum

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

    status: Optional[str]
    platform_url: Optional[str]
    terminal_url: Optional[str]
    terminal_dt: Optional[str]
    extra: Optional[Dict[str, Any]]

class DatasetPlatformItem(BaseModel):
    platform_name: str
    platform_status: str
    manifest: Optional[List[FilesetManifestFile]]

    platform_domain: Optional[str]
    platform_id: Optional[str]
    archiveorg_item_name: Optional[str]
    archiveorg_collection: Optional[str]
    web_base_url: Optional[str]
    web_bundle_url: Optional[str]

class ArchiveStrategyResult(BaseModel):
    ingest_strategy: str
    status: str
    manifest: List[FilesetManifestFile]
