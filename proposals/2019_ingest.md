
status: work-in-progress

This document proposes structure and systems for ingesting (crawling) paper
PDFs and other content as part of sandcrawler.

## Overview

The main abstraction is a sandcrawler "ingest request" object, which can be
created and submitted to one of several systems for automatic harvesting,
resulting in an "ingest result" metadata object. This result should contain
enough metadata to be automatically imported into fatcat as a file/release
mapping.

The structure and pipelines should be flexible enough to work with individual
PDF files, web captures, and datasets. It should work for on-demand
(interactive) ingest (for "save paper now" features), soft-real-time
(hourly/daily/queued), batches of hundreds or thousands of requests, and scale
up to batch ingest crawls of tens of millions of URLs. Most code should not
care about how or when content is actually crawled.

The motivation for this structure is to consolidate and automate the current ad
hoc systems for crawling, matching, and importing into fatcat. It is likely
that there will still be a few special cases with their own importers, but the
goal is that in almost all cases that we discover a new structured source of
content to ingest (eg, a new manifest of identifiers to URLs), we can quickly
transform the task into a list of ingest requests, then submit those requests
to an automated system to have them archived and inserted into fatcat with as
little manual effort as possible.

## Use Cases and Workflows

### Unpaywall Example

As a motivating example, consider how unpaywall crawls are done today:

- download and archive JSON dump from unpaywall. transform and filter into a
  TSV with DOI, URL, release-stage columns.
- filter out previously crawled URLs from this seed file, based on last dump,
  with the intent of not repeating crawls unnecessarily
- run heritrix3 crawl, usually by sharding seedlist over multiple machines.
  after crawl completes:
    - backfill CDX PDF subset into hbase (for future de-dupe)
    - generate CRL files etc and upload to archive items
- run arabesque over complete crawl logs. this takes time, is somewhat manual,
  and has scaling issues past a few million seeds
- depending on source/context, run fatcat import with arabesque results
- periodically run GROBID (and other transforms) over all new harvested files

Issues with this are:

- seedlist generation and arabesque step are toilsome (manual), and arabesque
  likely has metadata issues or otherwise "leaks" content
- brozzler pipeline is entirely separate
- results in re-crawls of content already in wayback, in particular links
  between large corpuses

New plan:

- download dump, filter, transform into ingest requests (mostly the same as
  before)
- load into ingest-request SQL table. only new rows (unique by source, type,
  and URL) are loaded. run a SQL query for new rows from the source with URLs
  that have not been ingested
- (optional) pre-crawl bulk/direct URLs using heritrix3, as before, to reduce
  later load on SPN
- run ingest script over the above SQL output. ingest first hits CDX/wayback,
  and falls back to SPNv2 (brozzler) for "hard" requests, or based on URL.
  ingest worker handles file metadata, GROBID, any other processing. results go
  to kafka, then SQL table
- either do a bulk fatcat import (via join query), or just have workers
  continuously import into fatcat from kafka ingest feed (with various quality
  checks)

## Request/Response Schema

For now, plan is to have a single request type, and multiple similar but
separate result types, depending on the ingest type (file, fileset,
webcapture). The initial use case is single file PDF ingest.

NOTE: what about crawl requests where we don't know if we will get a PDF or
HTML? Or both? Let's just recrawl.

*IngestRequest*
  - `ingest_type`: required, one of `pdf`, `xml`, `html`, `dataset`. For
    backwards compatibility, `file` should be interpreted as `pdf`. `pdf` and
    `xml` return file ingest respose; `html` and `dataset` not implemented but
    would be webcapture (wayback) and fileset (archive.org item or wayback?).
    In the future: `epub`, `video`, `git`, etc.
  - `base_url`: required, where to start crawl process
  - `link_source`: recommended, slug string. indicating the database or "authority"
    where URL/identifier match is coming from (eg, `doi`, `pmc`, `unpaywall`
    (doi), `s2` (semantic-scholar id), `spn` (fatcat release), `core` (CORE
    id), `mag` (MAG id))
  - `link_source_id`: recommended, identifier string. pairs with `link_source`.
  - `ingest_request_source`: recommended, slug string. tracks the service or
    user who submitted request. eg, `fatcat-changelog`, `editor_<ident>`,
    `savepapernow-web`
  - `release_stage`: optional. indicates the release stage of fulltext expected to be found at this URL
  - `fatcat`
    - `release_ident`: optional. if provided, indicates that ingest is expected
      to be fulltext copy of this release (though may be a sibling release
      under same work if `release_stage` doesn't match)
    - `work_ident`: optional, unused. might eventually be used if, eg,
      `release_stage` of ingested file doesn't match that of the `release_ident`
    - `edit_extra`: additional metadata to be included in any eventual fatcat
      commits.
  - `ext_ids`: matching fatcat schema. used for later lookups. sometimes
    `link_source` and id are sufficient.
    - `doi`
    - `pmcid`
    - ...

*FileIngestResult*
  - request (object): the full IngestRequest, copied
  - terminal
    - url
    - status_code
  - wayback (XXX: ?)
    - datetime
    - archive_url
  - file_meta (same schema as sandcrawler-db table)
    - size_bytes
    - md5
    - sha1
    - sha256
    - mimetype
  - cdx (same schema as sandcrawler-db table)
  - grobid (same schema as sandcrawler-db table)
    - status
    - grobid_version
    - status_code
    - xml_url
    - fatcat_release (via biblio-glutton match)
    - metadata (JSON)
  - status (slug): 'success', 'error', etc
  - hit (boolean): whether we got something that looks like what was requested

## New SQL Tables

Sandcrawler should persist status about:

- claimed locations (links) to fulltext copies of in-scope works, from indexes
  like unpaywall, MAG, semantic scholar, CORE
    - with enough context to help insert into fatcat if works are crawled and
      found. eg, external identifier that is indexed in fatcat, and
      release-stage
- state of attempting to crawl all such links
    - again, enough to insert into fatcat
    - also info about when/how crawl happened, particularly for failures, so we
      can do retries

Proposing two tables:

    -- source/source_id examples:
    --  unpaywall / doi
    --  mag / mag_id
    --  core / core_id
    --  s2 / semanticscholar_id
    --  doi / doi (for any base_url which is just https://doi.org/10..., regardless of why enqueued)
    --  pmc / pmcid (for any base_url like europmc.org, regardless of why enqueued)
    --  arxiv / arxiv_id (for any base_url like arxiv.org, regardless of why enqueued)
    CREATE TABLE IF NOT EXISTS ingest_request (
        -- conceptually: source, source_id, ingest_type, url
        -- but we use this order for PRIMARY KEY so we have a free index on type/URL
        ingest_type             TEXT NOT NULL CHECK (octet_length(ingest_type) >= 1),
        base_url                TEXT NOT NULL CHECK (octet_length(url) >= 1),
        link_source             TEXT NOT NULL CHECK (octet_length(link_source) >= 1),
        link_source_id          TEXT NOT NULL CHECK (octet_length(link_source_id) >= 1),

        created                 TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        release_stage           TEXT CHECK (octet_length(release_stage) >= 1),
        request                 JSONB,
        -- request isn't required, but can stash extra fields there for import, eg:
        --   ext_ids (source/source_id sometimes enough)
        --   release_ident (if ext_ids and source/source_id not specific enough; eg SPN)
        --   edit_extra
        -- ingest_request_source   TEXT NOT NULL CHECK (octet_length(ingest_request_source) >= 1),

        PRIMARY KEY (ingest_type, base_url, link_source, link_source_id)
    );

    CREATE TABLE IF NOT EXISTS ingest_file_result (
        ingest_type             TEXT NOT NULL CHECK (octet_length(ingest_type) >= 1),
        base_url                TEXT NOT NULL CHECK (octet_length(url) >= 1),

        updated                 TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        hit                     BOOLEAN NOT NULL,
        status                  TEXT
        terminal_url            TEXT, INDEX
        terminal_dt             TEXT
        terminal_status_code    INT
        terminal_sha1hex        TEXT, INDEX

        PRIMARY KEY (ingest_type, base_url)
    );

## New Kafka Topics

- `sandcrawler-ENV.ingest-file-requests`
- `sandcrawler-ENV.ingest-file-results`

## Ingest Tool Design

The basics of the ingest tool are to:

- use native wayback python library to do fast/efficient lookups and redirect
  lookups
- starting from base-url, do a fetch to either target resource or landing page:
  follow redirects, at terminus should have both CDX metadata and response body
    - if no capture, or most recent is too old (based on request param), do
      SPNv2 (brozzler) fetches before wayback lookups
- if looking for PDF but got landing page (HTML), try to extract a PDF link
  from HTML using various tricks, then do another fetch. limit this
  recursion/spidering to just landing page (or at most one or two additional
  hops)

Note that if we pre-crawled with heritrix3 (with `citation_pdf_url` link
following), then in the large majority of simple cases we

## Design Issues

### Open Questions

Do direct aggregator/repositories crawls need to go through this process? Eg
arxiv.org or pubmed central. I guess so, otherwise how do we get full file
metadata (size, other hashes)?

When recording hit status for a URL (ingest result), is that status dependent
on the crawl context? Eg, for save-paper-now we might want to require GROBID.
Semantics of `hit` should probably be consistent: if we got the filetype
expected based on type, not whether we would actually import to fatcat.

Where to include knowledge about, eg, single-page abstract PDFs being bogus? Do
we just block crawling, set an ingest result status, or only filter at fatcat
import time? Definitely need to filter at fatcat import time to make sure
things don't slip through elsewhere.

### Yet Another PDF Harvester

This system could result in "yet another" set of publisher-specific heuristics
and hacks to crawl publicly available papers. Related existing work includes
[unpaywall's crawler][unpaywall_crawl], LOCKSS extraction code, dissem.in's
efforts, zotero's bibliography extractor, etc. The "memento tracer" work is
also similar. Many of these are even in python! It would be great to reduce
duplicated work and maintenance. An analagous system in the wild is youtube-dl
for downloading video from many sources.

[unpaywall_crawl]: https://github.com/ourresearch/oadoi/blob/master/webpage.py
[memento_tracer]: http://tracer.mementoweb.org/

One argument against this would be that our use-case is closely tied to
save-page-now, wayback, and the CDX API. However, a properly modular
implementation of a paper downloader would allow components to be re-used, and
perhaps dependency ingjection for things like HTTP fetches to allow use of SPN
or similar. Another argument for modularity would be support for headless
crawling (eg, brozzler).

Note that this is an internal implementation detail; the ingest API would
abstract all this.

## Test Examples

Some example works that are difficult to crawl. Should have mechanisms to crawl
and unit tests for all these.

- <https://pubs.acs.org>
- <https://linkinghub.elsevier.com> / <https://sciencedirect.com>
- <https://www.osapublishing.org/captcha/?guid=39B0E947-C0FC-B5D8-2C0C-CCF004FF16B8>
- <https://utpjournals.press/action/cookieAbsent>
- <https://academic.oup.com/jes/article/3/Supplement_1/SUN-203/5484104>
- <http://www.jcancer.org/v10p4038.htm>
