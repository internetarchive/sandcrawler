
status: planned

2020q1 Fulltext PDF Ingest Plan
===================================

This document lays out a plan and tasks for a push on crawling and ingesting
more fulltext PDF content in early 2020.

The goal is to get the current generation of pipelines and matching tools
running smoothly by the end of March, when the Mellon phase 1 grant ends. As a
"soft" goal, would love to see over 25 million papers (works) with fulltext in
fatcat by that deadline as well.

This document is organized by conceptual approach, then by jobs to run and
coding tasks needing work.

There is a lot of work here!


## Broad OA Ingest By External Identifier

There are a few million papers in fatacat which:

1. have a DOI, arxiv id, or pubmed central id, which can be followed to a
   landing page or directly to a PDF
2. are known OA, usually because publication is Gold OA
3. don't have any fulltext PDF in fatcat

As a detail, some of these "known OA" journals actually have embargoes (aka,
they aren't true Gold OA). In particular, those marked via EZB OA "color", and
recent pubmed central ids.

Of these, I think there are broadly two categories. The first is just papers we
haven't tried directly crawling or ingesting yet at all; these should be easy
to crawl and ingest. The second category is papers from large publishers with
difficult to crawl landing pages (for example, Elsevier, IEEE, Wiley, ACM). The
later category will probably not crawl with heritrix, and we are likely to be
rate-limited or resource constrained when using brozzler or 

Coding Tasks:

- improve `fatcat_ingest.py` script to allow more granular slicing and limiting
  the number of requests enqueued per batch (eg, to allow daily partial
  big-publisher ingests in random order). Allow dumping arxiv+pmcid ingest
  requests.

Actions:

- run broad Datacite DOI landing crawl with heritrix ("pre-ingest")
- after Datacite crawl completes, run arabesque and ingest any PDF hits
- run broad non-Datacite DOI landing crawl with heritrix. Use ingest tool to
  generate (or filter a dump), removing Datacite DOIs and large publishers
- after non-Datacite crawl completes, run entire ingest request set through in
  bulk mode
- start enqueing large-publisher (hard to crawl) OA DOIs to ingest queue
  for SPNv2 crawling (blocking ingest tool improvement, and also SPNv2 health)
- start new PUBMEDCENTRAL and ARXIV slow-burn pubmed crawls (heritrix). Use
  updated ingest tool to generate requests.


## Large Seedlist Crawl Iterations

We have a bunch of large, high quality seedlists, most of which haven't been
updated or crawled in a year or two. Some use DOIs as identifiers, some use an
internal identifier. As a quick summary:

- unpaywall: currently 25 million DOIs (Crossref only?) with fulltext. URLs may
  be doi.org, publisher landing page, or direct PDF; may be published version,
  pre-print, or manuscript (indicated with a flag). Only crawled with heritrix;
  last crawl was Spring 2019.  There is a new dump from late 2019 with a couple
  million new papers/URLs.
- microsoft academic (MAG): tens of millions of papers, hundreds of millions of
  URLs. Last crawled 2018 (?) from a 2016 dump. Getting a new full dump via
  Azure; new dump includes type info for each URL ("pdf", "landing page", etc).
  Uses MAG id for each URL, not DOI; hoping new dump has better MAG/DOI
  mappings. Expect a very large crawl (tens of millions of new URLs).
- CORE: can do direct crawling of PDFs from their site, as well as external
  URLs. They largely have pre-prints and IR content. Have not released a dump
  in a long time. Would expect a couple million new direct (core.ac.uk) URLs
  and fewer new web URLs (often overlap with other lists, like MAG)
- semantic scholar: they do regular dumps. Use SHA1 hash of PDF as identifier;
  it's the "best PDF of a group", so not always the PDF you crawl. Host many OA
  PDFs on their domain, very fast to crawl, as well as wide-web URLs. Their
  scope has increased dramatically in recent years due to MAG import; expect a
  lot of overlap there.

It is increasingly important to not 

Coding Tasks:
- transform scripts for all these seedlist sources to create ingest request
  lists
- sandcrawler ingest request persist script, which supports setting datetime
- fix HBase thrift gateway so url agnostic de-dupe can be updated
- finish ingest worker "skip existing" code path, which looks in sandcrawler-db
  to see if URL has already been processed (for efficiency)

Actions:
- transform and persist all these old seedlists, with the URL datetime set to
  roughly when the URL was added to the upstream corpus
- transform arabesque output for all old crawls into ingest requests and run
  through the bulk ingest queue. expect GROBID to be skipped for all these, and
  for the *requests* not to be updated (SQL ON CONFLICT DO NOTHING). Will
  update ingest result table with status.
- fetch new MAG and unpaywall seedlists, transform to ingest requests, persist
  into ingest request table. use SQL to dump only the *new* URLs (not seen in
  previous dumps) using the created timestamp, outputting new bulk ingest
  request lists. if possible, de-dupe between these two. then start bulk
  heritrix crawls over these two long lists. Probably sharded over several
  machines. Could also run serially (first one, then the other, with
  ingest/de-dupe in between). Filter out usual large sites (core, s2, arxiv,
  pubmed, etc)
- CORE and Semantic Scholar direct crawls, of only new URLs on their domain
  (should not significantly conflict/dupe with other bulk crawls)

After this round of big crawls completes we could do iterated crawling of
smaller seedlists, re-visit URLs that failed to ingest with updated heritrix
configs or the SPNv2 ingest tool, etc.


## GROBID/glutton Matching of Known PDFs

Of the many PDFs in the sandcrawler CDX "working set", many were broadly
crawled or added via CDX heuristic. In other words, we don't have an identifier
from a seedlist. We previously run a matching script in Hadoop that attempted
to link these to Crossref DOIs based on GROBID extracted metadata. We haven't
done this in a long time; in the meanwhile we have added many more such PDFs,
added lots of metadata to our matching set (eg, pubmed and arxiv in addition to
crossref), and have the new biblio-glutton tool for matching, which may work
better than our old conservative tool.

We have run GROBID+glutton over basically all of these PDFs. We should be able
to do a SQL query to select PDFs that:

- have at least one known CDX row
- GROBID processed successfully and glutton matched to a fatcat release
- do not have an existing fatcat file (based on sha1hex)
- output GROBID metadata, `file_meta`, and one or more CDX rows

An update match importer can take this output and create new file entities.
Then lookup the release and confirm the match to the GROBID metadata, as well
as any other quality checks, then import into fatcat. We have some existing
filter code we could use. The verification code should be refactored into a
reusable method.

It isn't clear to me how many new files/matches we would get from this, but
could do some test SQL queries to check. At least a million?

A related task is to update the glutton lookup table (elasticsearch index and
on-disk lookup tables) after more recent metadata imports (Datacite, etc).
Unsure if we should filter out records or improve matching so that we don't
match "header" (paper) metadata to non-paper records (like datasets), but still
allow *reference* matching (citations to datasets).

Coding Tasks:
- write SQL select function. Optionally, come up with a way to get multiple CDX
  rows in the output (sub-query?)
- biblio metadata verify match function (between GROBID metadata and existing
  fatcat release entity)
- updated match fatcat importer

Actions:
- update `fatcat_file` sandcrawler table
- check how many PDFs this might amount to. both by uniq SHA1 and uniq
  `fatcat_release` matches
- do some manual random QA verification to check that this method results in
  quality content in fatcat
- run full updated import


## No-Identifier PDF New Release Import Pipeline

Previously, as part of longtail OA crawling work, I took a set of PDFs crawled
from OA journal homepages (where the publisher does not register DOIs), took
successful GROBID metadata, filtered for metadata quality, and imported about
1.5 million new release entities into fatcat.

There were a number of metadata issues with this import that we are still
cleaning up, eg:

- paper actually did have a DOI and should have been associated with existing
  fatcat release entity; these PDFs mostly came from repository sites which
  aggregated many PDFs, or due to unintentional outlink crawl configs
- no container linkage for any of these releases, making coverage tracking or
  reporting difficult
- many duplicates in same import set, due to near-identical PDFs (different by
  SHA-1, but same content and metadata), not merged or grouped in any way

The cleanup process is out of scope for this document, but we want to do
another round of similar imports, while avoiding these problems.

As a rouch sketch of what this would look like (may need to iterate):

- filter to PDFs from longtail OA crawls (eg, based on WARC prefix, or URL domain)
- filter to PDFs not in fatcat already (in sandcrawler, then verify with lookup)
- filter to PDFs with successful GROBID extraction and *no* glutton match
- filter/clean GROBID extracted metadata (in python, not SQL), removing stubs
  or poor/partial extracts
- run a fuzzy biblio metadata match against fatcat elasticsearch; use match
  verification routine to check results
- if fuzzy match was a hit, consider importing directly as a matched file
  (especially if there are no existing files for the release)
- identify container for PDF from any of: domain pattern/domain; GROBID
  extracted ISSN or journal name; any other heuristic
- if all these filters pass and there was no fuzzy release match, and there was
  a container match, import a new release (and the file) into fatcat

Not entirely clear how to solve the near-duplicate issue. Randomize import
order (eg, sort by file sha1), import slowly with a single thread, and ensure
elasticsearch re-indexing pipeline is running smoothly so the fuzzy match will
find recently-imported hits?

In theory we could use biblio-glutton API to do the matching lookups, but I
think it will be almost as fast to hit our own elasticsearch index. Also the
glutton backing store is always likely to be out of date. In the future we may
even write something glutton-compatible that hits our index. Note that this is
also very similar to how citation matching could work, though it might be
derailing or over-engineering to come up with a single solution for both
applications at this time.

A potential issue here is that many of these papers are probably already in
another large but non-authoritative metadata corpus, like MAG, CORE, SHARE, or
BASE. Importing from those corpuses would want to go through the same fuzzy
matching to ensure we aren't creating duplicate releases, but further it would
be nice to be matching those external identifiers for any newly created
releases. One approach would be to bulk-import metadata from those sources
first. There are huge numbers of records in those corpuses, so we would need to
filter down by journal/container or OA flag first. Another would be to do fuzzy
matching when we *do* end up importing those corpuses, and update these records
with the external identifiers. This issue really gets at the crux of a bunch of
design issues and scaling problems with fatcat! But I think we should or need
to make progress on these longtail OA imports without perfectly solving these
larger issues.

Details/Questions:
- what about non-DOI metadata sources like MAG, CORE, SHARE, BASE? Should we
  import those first, or do fuzzy matching against those?
- use GROBID language detection and copy results to newly created releases
- in single-threaded, could cache "recently matched/imported releases" locally
  to prevent double-importing
- cache container matching locally

Coding Tasks:
- write SQL select statement
- iterate on GROBID metadata cleaning/transform/filter (have existing code for
  this somewhere)
- implement a "fuzzy match" routine that takes biblio metadata (eg, GROBID
  extracted), looks in fatcat elasticsearch for a match
- implement "fuzzy container match" routine, using as much available info as
  possible. Could use chocula sqlite locally, or hit elasticsearch container
  endpoint
- update GROBID importer to use fuzzy match and other checks

Actions:
- run SQL select and estimate bounds on number of new releases created
- do some manual randomized QA runs to ensure this pipeline is importing
  quality content in fatcat
- run a full batch import


## Non-authoritative Metadata and Fulltext from Aggregators

This is not fully thought through, but at some point we will probably add one
or more large external aggregator metadata sources (MAG, Semantic Scholar,
CORE, SHARE, BASE), and bulk import both metadata records and fulltext at the
same time. The assumption is that those sources are doing the same fuzzy entity
merging/de-dupe and crawling we are doing, but they have already done it
(probably with more resources) and created stable identifiers that we can
include.

A major blocker for most such imports is metadata licensing (fatcat is CC0,
others have restrictions). This may not be the case for CORE and SHARE though.
