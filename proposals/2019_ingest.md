
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

## Request/Response Schema

For now, plan is to have a single request type, and multiple similar but
separate result types, depending on the ingest type (file, fileset,
webcapture). The initial use case is single file PDF ingest.

NOTE: what about crawl requests where we don't know if we will get a PDF or
HTML? Or both?

*IngestRequest*
  - `ingest_type`: required, one of `file`, `fileset`, or `webcapture`
  - `base_url`: required, where to start crawl process
  - `project`/`source`: recommended, slug string. to track where this ingest
    request is coming from
  - `fatcat`
    - `release_stage`: optional
    - `release_ident`: optional
    - `work_ident`: optional
    - `edit_extra`: additional metadata to be included in any eventual fatcat
      commits. supplements project/source
  - `ext_ids`
    - `doi`
    - `pmcid`
    - ...
  - `expect_mimetypes`: 
  - `expect_hash`: optional, if we are expecting a specific file
    - `sha1`
    - ...

*FileIngestResult*
  - request (object): the full IngestRequest, copied
  - terminal
    - url
    - status_code
  - wayback
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
    - version
    - status_code
    - xml_url
    - release_id
  - status (slug): 'success', 'error', etc
  - hit (boolean): whether we got something that looks like what was requested

## Result Schema

## New API Endpoints

## New Kafka Topics

- `sandcrawler-ENV.ingest-file-requests`
- `sandcrawler-ENV.ingest-file-results`

## New Fatcat Features

## Design Issues

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
