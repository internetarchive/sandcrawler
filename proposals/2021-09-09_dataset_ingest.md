
Dataset Ingest Pipeline
=======================

Sandcrawler currently has ingest support for individual files saved as `file`
entities in fatcat (xml and pdf ingest types) and HTML files with
sub-components saved as `webcapture` entities in fatcat (html ingest type).

This document describes extensions to this ingest system to flexibly support
groups of files, which may be represented in fatcat as `fileset` entities. The
new ingest type is `dataset`.

Compared to the existing ingest process, there are two major complications with
datasets:

- the ingest process often requires more than parsing HTML files, and will be
  specific to individual platforms and host software packages
- the storage backend and fatcat entity type is flexible: a dataset might be
  represented by a single file, multiple files combined in to a single .zip
  file, or mulitple separate files; the data may get archived in wayback or in
  an archive.org item

The new concepts of "strategy" and "platform" are introduced to accomodate
these complications.


## Ingest Strategies

The ingest strategy describes the fatcat entity type that will be output; the
storage backend used; and whether an enclosing file format is used. The
strategy to use can not be determined until the number and size of files is
known. It is a function of file count, total file size, and platform.

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

"Bundle" files are things like .zip or .tar.gz. Not all .zip files are handled
as bundles! Only when the transfer from the hosting platform is via a "download
all as .zip" (or similar) do we consider a zipfile a "bundle" and index the
interior files as a fileset.

The term "bundle file" is used over "archive file" or "container file" to
prevent confusion with the other use of those terms in the context of fatcat
(container entities; archive; Internet Archive as an organiztion).

The motivation for supporting both `web` and `archiveorg` is that `web` is
somewhat simpler for small files, but `archiveorg` is better for larger groups
of files (say more than 20) and larger total size (say more than 1 GByte total,
or 128 MByte for any one file).

The motivation for supporting "bundled" filesets is that there is only a single
file to archive.


## Ingest Pseudocode

1. Determine `platform`, which may involve resolving redirects and crawling a landing page.

  a. TODO: do we always try crawling `base_url`? would simplify code flow, but results in extra SPN calls (slow). start with yes, always
  b. TODO: what if we trivially crawl directly to a non-HTML file? Bypass most of the below? `direct-file` strategy?
  c. `infer_platform(request, terminal_url, html_biblio)`

2. Use platform-specific methods to fetch manifest metadata and decide on an `ingest_strategy`.

3. Use strategy-specific methods to archive all files in platform manifest, and verify manifest metadata.

4. Summarize status and return structured result metadata.

Python APIs, as abstract classes (TODO):

    PlatformDatasetContext
        platform_name
        platform_domain
        platform_id
        manifest
        archiveorg_metadata
        web_base_url
    DatasetPlatformHelper
        match_request(request: Request, resource: Resource, html_biblio: Optional[BiblioMetadata]) -> bool
        process_request(?) -> ?
    StrategyArchiver
        process(manifest, archiveorg_metadata, web_metadata) -> ?
        check_existing(?) -> ?


## New Sandcrawler Code and Worker

    sandcrawler-ingest-fileset-worker@{1..12}

Worker consumes from ingest request topic, produces to fileset ingest results,
and optionally produces to file ingest results.

    sandcrawler-persist-ingest-fileset-worker@1

Simply writes fileset ingest rows in to SQL.

## New Fatcat Worker and Code Changes

    fatcat-import-ingest-fileset-worker

This importer should be modeled on file and web worker. Filters for `success`
with strategy of `*-fileset*`.

Existing `fatcat-import-ingest-file-worker` should be updated to allow
`dataset` single-file imports, with largely same behavior and semantics as
current importer.

TODO: Existing fatcat transforms, and possibly even elasticsearch schemas,
should be updated to include fileset status and `in_ia` flag for dataset type
releases.

TODO: Existing entity updates worker submits `dataset` type ingests to ingest
request topic.


## New SQL Tables

    CREATE TABLE IF NOT EXISTS ingest_fileset_result (
        ingest_type             TEXT NOT NULL CHECK (octet_length(ingest_type) >= 1),
        base_url                TEXT NOT NULL CHECK (octet_length(base_url) >= 1),
        updated                 TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        hit                     BOOLEAN NOT NULL,
        status                  TEXT CHECK (octet_length(status) >= 1),

        terminal_url            TEXT CHECK (octet_length(terminal_url) >= 1),
        terminal_dt             TEXT CHECK (octet_length(terminal_dt) = 14),
        terminal_status_code    INT,
        terminal_sha1hex        TEXT CHECK (octet_length(terminal_sha1hex) = 40),

        platform                TEXT CHECK (octet_length(platform) >= 1),
        platform_domain         TEXT CHECK (octet_length(platform_domain) >= 1),
        platform_id             TEXT CHECK (octet_length(platform_id) >= 1),
        ingest_strategy         TEXT CHECK (octet_length(ingest_strategy) >= 1),
        total_size              BIGINT,
        file_count              INT,
        item_name               TEXT CHECK (octet_length(item_name) >= 1),
        item_bundle_path        TEXT CHECK (octet_length(item_path_bundle) >= 1),

        manifest                JSONB,
        -- list, similar to fatcat fileset manifest, plus extra:
        --   status (str)
        --   path (str)
        --   size (int)
        --   md5 (str)
        --   sha1 (str)
        --   sha256 (str)
        --   mimetype (str)
        --   platform_url (str)
        --   terminal_url (str)
        --   terminal_dt (str)
        --   extra (dict) (?)

        PRIMARY KEY (ingest_type, base_url)
    );
    CREATE INDEX ingest_fileset_result_terminal_url_idx ON ingest_fileset_result(terminal_url);


## New Kafka Topic and JSON Schema

    
    sandcrawler-ENV.ingest-fileset-results 6x, no retention limit


## Implementation Plan

First implement ingest worker, including platform and strategy helpers, and
test those as simple stdin/stdout CLI tools in sandcrawler repo to validate
this proposal.

Second implement fatcat importer and test locally and/or in QA.

Lastly implement infrastructure, automation, and other "glue".

