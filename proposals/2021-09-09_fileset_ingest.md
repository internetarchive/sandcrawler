
status: implemented

Fileset Ingest Pipeline (for Datasets)
======================================

Sandcrawler currently has ingest support for individual files saved as `file`
entities in fatcat (xml and pdf ingest types) and HTML files with
sub-components saved as `webcapture` entities in fatcat (html ingest type).

This document describes extensions to this ingest system to flexibly support
groups of files, which may be represented in fatcat as `fileset` entities. The
main new ingest type is `dataset`.

Compared to the existing ingest process, there are two major complications with
datasets:

- the ingest process often requires more than parsing HTML files, and will be
  specific to individual platforms and host software packages
- the storage backend and fatcat entity type is flexible: a dataset might be
  represented by a single file, multiple files combined in to a single .zip
  file, or multiple separate files; the data may get archived in wayback or in
  an archive.org item

The new concepts of "strategy" and "platform" are introduced to accommodate
these complications.


## Ingest Strategies

The ingest strategy describes the fatcat entity type that will be output; the
storage backend used; and whether an enclosing file format is used. The
strategy to use can not be determined until the number and size of files is
known. It is a function of file count, total file size, and publication
platform.

Strategy names are compact strings with the format
`{storage_backend}-{fatcat_entity}`. A `-bundled` suffix after a `fileset`
entity type indicates that metadata about multiple files is retained, but that
in the storage backend only a single enclosing file (eg, `.zip`) will be
stored.

The supported strategies are:

- `web-file`: single file of any type, stored in wayback, represented as fatcat `file`
- `web-fileset`: multiple files of any type, stored in wayback, represented as fatcat `fileset`
- `web-fileset-bundled`: single bundle file, stored in wayback, represented as fatcat `fileset`
- `archiveorg-file`: single file of any type, stored in archive.org item, represented as fatcat `file`
- `archiveorg-fileset`: multiple files of any type, stored in archive.org item, represented as fatcat `fileset`
- `archiveorg-fileset-bundled`: single bundle file, stored in archive.org item, represented as fatcat `fileset`

"Bundle" or "enclosing" files are things like .zip or .tar.gz. Not all .zip
files are handled as bundles! Only when the transfer from the hosting platform
is via a "download all as .zip" (or similar) do we consider a zipfile a
"bundle" and index the interior files as a fileset.

The term "bundle file" is used over "archive file" or "container file" to
prevent confusion with the other use of those terms in the context of fatcat
(container entities; archive; Internet Archive as an organization).

The motivation for supporting both `web` and `archiveorg` is that `web` is
somewhat simpler for small files, but `archiveorg` is better for larger groups
of files (say more than 20) and larger total size (say more than 1 GByte total,
or 128 MByte for any one file).

The motivation for supporting "bundled" filesets is that there is only a single
file to archive.


## Ingest Pseudocode

1. Determine `platform`, which may involve resolving redirects and crawling a landing page.

  a. currently we always crawl the ingest `base_url`, capturing a platform landing page
  b. we don't currently handle the case of `base_url` leading to a non-HTML
     terminal resource. the `component` ingest type does handle this

2. Use platform-specific methods to fetch manifest metadata and decide on an `ingest_strategy`.

  a. depending on platform, may include access URLs for multiple strategies
     (eg, URL for each file and a bundle URL), metadata about the item for, eg,
     archive.org item upload, etc

3. Use strategy-specific methods to archive all files in platform manifest, and verify manifest metadata.

4. Summarize status and return structured result metadata.

  a. if the strategy was `web-file` or `archiveorg-file`, potentially submit an
  `ingest_file_result` object down the file ingest pipeline (Kafka topic and
  later persist and fatcat import workers), with `dataset-file` ingest
  type (or `{ingest_type}-file` more generally).

New python types:

    FilesetManifestFile
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

    FilesetPlatformItem
        platform_name: str
        platform_status: str
        platform_domain: Optional[str]
        platform_id: Optional[str]
        manifest: Optional[List[FilesetManifestFile]]
        archiveorg_item_name: Optional[str]
        archiveorg_item_meta
        web_base_url
        web_bundle_url

    ArchiveStrategyResult
        ingest_strategy: str
        status: str
        manifest: List[FilesetManifestFile]
        file_file_meta: Optional[dict]
        file_terminal: Optional[dict]
        file_cdx: Optional[dict]
        bundle_file_meta: Optional[dict]
        bundle_terminal: Optional[dict]
        bundle_cdx: Optional[dict]
        bundle_archiveorg_path: Optional[dict]

New python APIs/classes:

    FilesetPlatformHelper
        match_request(request, resource, html_biblio) -> bool
            does the request and landing page metadata indicate a match for this platform?
        process_request(request, resource, html_biblio) -> FilesetPlatformItem
            do API requests, parsing, etc to fetch metadata and access URLs for this fileset/dataset. platform-specific
        chose_strategy(item: FilesetPlatformItem) -> IngestStrategy
            select an archive strategy for the given fileset/dataset

    FilesetIngestStrategy
        check_existing(item: FilesetPlatformItem) -> Optional[ArchiveStrategyResult]
            check the given backend for an existing capture/archive; if found, return result
        process(item: FilesetPlatformItem) -> ArchiveStrategyResult
            perform an actual archival capture

## Limits and Failure Modes

- `too-large-size`: total size of the fileset is too large for archiving.
  initial limit is 64 GBytes, controlled by `max_total_size` parameter.
- `too-many-files`: number of files (and thus file-level metadata) is too
  large. initial limit is 200, controlled by `max_file_count` parameter.
- `platform-scope / FilesetPlatformScopeError`: for when `base_url` leads to a
  valid platform, which could be found via API or parsing, but has the wrong
  scope. Eg, tried to fetch a dataset, but got a DOI which represents all
  versions of the dataset, not a specific version.
- `platform-restricted`/`PlatformRestrictedError`: for, eg, embargoes 
- `platform-404`: got to a landing page, and seemed like in-scope, but no
  platform record found anyways


## New Sandcrawler Code and Worker

    sandcrawler-ingest-fileset-worker@{1..6}  (or up to 1..12 later)

Worker consumes from ingest request topic, produces to fileset ingest results,
and optionally produces to file ingest results.

    sandcrawler-persist-ingest-fileset-worker@1

Simply writes fileset ingest rows to SQL.


## New Fatcat Worker and Code Changes

    fatcat-import-ingest-fileset-worker

This importer is modeled on file and web worker. Filters for `success` with
strategy of `*-fileset*`.

Existing `fatcat-import-ingest-file-worker` should be updated to allow
`dataset` single-file imports, with largely same behavior and semantics as
current importer (`component` mode).

Existing fatcat transforms, and possibly even elasticsearch schemas, should be
updated to include fileset status and `in_ia` flag for dataset type releases.

Existing entity updates worker submits `dataset` type ingests to ingest request
topic.


## Ingest Result Schema

Common with file results, and mostly relating to landing page HTML:

    hit: bool
    status: str
        success
        success-existing
        success-file (for `web-file` or `archiveorg-file` only)
    request: object
    terminal: object
    file_meta: object
    cdx: object
    revisit_cdx: object
    html_biblio: object

Additional fileset-specific fields:

    manifest: list of objects
    platform_name: str
    platform_domain: str
    platform_id: str
    platform_base_url: str
    ingest_strategy: str
    archiveorg_item_name: str (optional, only for `archiveorg-*` strategies)
    file_count: int
    total_size: int
    fileset_bundle (optional, only for `*-fileset-bundle` strategy)
        file_meta
        cdx
        revisit_cdx
        terminal
        archiveorg_bundle_path
    fileset_file (optional, only for `*-file` strategy)
        file_meta
        terminal
        cdx
        revisit_cdx

If the strategy was `web-file` or `archiveorg-file` and the status is
`success-file`, then an ingest file result will also be published to
`sandcrawler-ENV.ingest-file-results`, using the same ingest type and fields as
regular ingest.


All fileset ingest results get published to ingest-fileset-result.

Existing sandcrawler persist workers also subscribe to this topic and persist
status and landing page terminal info to tables just like with file ingest.
GROBID, HTML, and other metadata is not persisted in this path.

If the ingest strategy was a single file (`*-file`), then an ingest file is
also published to the ingest-file-result topic, with the `fileset_file`
metadata, and ingest type `dataset-file`. This should only happen on success
condition.


## New SQL Tables

Note that this table *complements* `ingest_file_result`, doesn't replace it.
`ingest_file_result` could more accurately be called `ingest_result`.

    CREATE TABLE IF NOT EXISTS ingest_fileset_platform (
        ingest_type             TEXT NOT NULL CHECK (octet_length(ingest_type) >= 1),
        base_url                TEXT NOT NULL CHECK (octet_length(base_url) >= 1),
        updated                 TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        hit                     BOOLEAN NOT NULL,
        status                  TEXT CHECK (octet_length(status) >= 1),

        platform_name           TEXT NOT NULL CHECK (octet_length(platform_name) >= 1),
        platform_domain         TEXT NOT NULL CHECK (octet_length(platform_domain) >= 1),
        platform_id             TEXT NOT NULL CHECK (octet_length(platform_id) >= 1),
        ingest_strategy         TEXT CHECK (octet_length(ingest_strategy) >= 1),
        total_size              BIGINT,
        file_count              BIGINT,
        archiveorg_item_name    TEXT CHECK (octet_length(archiveorg_item_name) >= 1),

        archiveorg_item_bundle_path TEXT CHECK (octet_length(archiveorg_item_bundle_path) >= 1),
        web_bundle_url          TEXT CHECK (octet_length(web_bundle_url) >= 1),
        web_bundle_dt           TEXT CHECK (octet_length(web_bundle_dt) = 14),

        manifest                JSONB,
        -- list, similar to fatcat fileset manifest, plus extra:
        --   status (str)
        --   path (str)
        --   size (int)
        --   md5 (str)
        --   sha1 (str)
        --   sha256 (str)
        --   mimetype (str)
        --   extra (dict)
        --   platform_url (str)
        --   terminal_url (str)
        --   terminal_dt (str)

        PRIMARY KEY (ingest_type, base_url)
    );
    CREATE INDEX ingest_fileset_platform_name_domain_id_idx ON ingest_fileset_platform(platform_name, platform_domain, platform_id);

Persist worker should only insert in to this table if `platform_name` is
identified.

## New Kafka Topic

    sandcrawler-ENV.ingest-fileset-results 6x, no retention limit


## Implementation Plan

First implement ingest worker, including platform and strategy helpers, and
test those as simple stdin/stdout CLI tools in sandcrawler repo to validate
this proposal.

Second implement fatcat importer and test locally and/or in QA.

Lastly implement infrastructure, automation, and other "glue":

- SQL schema
- persist worker


## Design Note: Single-File Datasets

Should datasets and other groups of files which only contain a single file get
imported as a fatcat `file` or `fileset`? This can be broken down further as
documents (single PDF) vs other individual files.

Advantages of `file`:

- handles case of article PDFs being marked as dataset accidentally
- `file` entities get de-duplicated with simple lookup (eg, on `sha1`)
- conceptually simpler if individual files are `file` entity
- easier to download individual files

Advantages of `fileset`:

- conceptually simpler if all `dataset` entities have `fileset` form factor
- code path is simpler: one fewer strategy, and less complexity of sending
  files down separate import path
- metadata about platform is retained
- would require no modification of existing fatcat file importer
- fatcat import of archive.org of `file` is not actually implemented yet?

Decision is to do individual files. Fatcat fileset import worker should reject
single-file (and empty) manifest filesets. Fatcat file import worker should
accept all mimetypes for `dataset-file` (similar to `component`).


## Example Entities

See `notes/dataset_examples.txt`
