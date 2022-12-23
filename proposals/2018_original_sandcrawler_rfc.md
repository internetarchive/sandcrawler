
**Title:** Journal Archiving Pipeline

**Author:** Bryan Newbold <bnewbold@archive.org>

**Date:** March 2018

**Status:** work-in-progress

This is an RFC-style technical proposal for a journal crawling, archiving,
extracting, resolving, and cataloging pipeline.

Design work funded by a Mellon Foundation grant in 2018.

## Overview

Let's start with data stores first:

- crawled original fulltext (PDF, JATS, HTML) ends up in petabox/global-wayback
- file-level extracted fulltext and metadata is stored in HBase, with the hash
  of the original file as the key
- cleaned metadata is stored in a "catalog" relational (SQL) database (probably
  PostgreSQL or some hip scalable NewSQL thing compatible with Postgres or
  MariaDB)

**Resources:** back-of-the-envelope, around 100 TB petabox storage total (for
100 million PDF files); 10-20 TB HBase table total. Can start small.


All "system" (aka, pipeline) state (eg, "what work has been done") is ephemeral
and is rederived relatively easily (but might be cached for performance).

The overall "top-down", metadata-driven cycle is:

1. Partners and public sources provide metadata (for catalog) and seed lists
   (for crawlers)
2. Crawlers pull in fulltext and HTTP/HTML metadata from the public web
3. Extractors parse raw fulltext files (PDFs) and store structured metadata (in
   HBase)
4. Data Mungers match extracted metadata (from HBase) against the catalog, or
   create new records if none found.

In the "bottom up" cycle, batch jobs run as map/reduce jobs against the
catalog, HBase, global wayback, and partner metadata datasets to identify
potential new public or already-archived content to process, and pushes tasks
to the crawlers, extractors, and mungers.

## Partner Metadata

Periodic Luigi scripts run on a regular VM to pull in metadata from partners.
All metadata is saved to either petabox (for public stuff) or HDFS (for
restricted). Scripts process/munge the data and push directly to the catalog
(for trusted/authoritative sources like Crossref, ISSN, PubMed, DOAJ); others
extract seedlists and push to the crawlers (

**Resources:** 1 VM (could be a devbox), with a large attached disk (spinning
probably ok)

## Crawling

All fulltext content comes in from the public web via crawling, and all crawled
content ends up in global wayback.

One or more VMs serve as perpetual crawlers, with multiple active ("perpetual")
Heritrix crawls operating with differing configuration. These could be
orchestrated (like h3), or just have the crawl jobs cut off and restarted every
year or so.

In a starter configuration, there would be two crawl queues. One would target
direct PDF links, landing pages, author homepages, DOI redirects, etc. It would
process HTML and look for PDF outlinks, but wouldn't crawl recursively.

HBase is used for de-dupe, with records (pointers) stored in WARCs.

A second config would take seeds as entire journal websites, and would crawl
continuously.

Other components of the system "push" tasks to the crawlers by copying schedule
files into the crawl action directories.

WARCs would be uploaded into petabox via draintasker as usual, and CDX
derivation would be left to the derive process. Other processes are notified of
"new crawl content" being available when they see new unprocessed CDX files in
items from specific collections. draintasker could be configured to "cut" new
items every 24 hours at most to ensure this pipeline moves along regularly, or
we could come up with other hacks to get lower "latency" at this stage.

**Resources:** 1-2 crawler VMs, each with a large attached disk (spinning)

### De-Dupe Efficiency

We would certainly feed CDX info from all bulk journal crawling into HBase
before any additional large crawling, to get that level of de-dupe.

As to whether all GWB PDFs should be de-dupe against is a policy question: is
there something special about the journal-specific crawls that makes it worth
having second copies? Eg, if we had previously domain crawled and access is
restricted, we then wouldn't be allowed to provide researcher access to those
files... on the other hand, we could extract for researchers given that we
"refound" the content at a new URL?

Only fulltext files (PDFs) would be de-duped against (by content), so we'd be
recrawling lots of HTML. Presumably this is a fraction of crawl data size; what
fraction?

Watermarked files would be refreshed repeatedly from the same PDF, and even
extracted/processed repeatedly (because the hash would be different). This is
hard to de-dupe/skip, because we would want to catch "content drift" (changes
in files).

## Extractors

Off-the-shelf PDF extraction software runs on high-CPU VM nodes (probably
GROBID running on 1-2 data nodes, which have 30+ CPU cores and plenty of RAM
and network throughput).

A hadoop streaming job (written in python) takes a CDX file as task input. It
filters for only PDFs, and then checks each line against HBase to see if it has
already been extracted. If it hasn't, the script downloads directly from
petabox using the full CDX info (bypassing wayback, which would be a
bottleneck). It optionally runs any "quick check" scripts to see if the PDF
should be skipped ("definitely not a scholarly work"), then if it looks Ok
submits the file over HTTP to the GROBID worker pool for extraction. The
results are pushed to HBase, and a short status line written to Hadoop. The
overall Hadoop job has a reduce phase that generates a human-meaningful report
of job status (eg, number of corrupt files) for monitoring.

A side job as part of extracting can "score" the extracted metadata to flag
problems with GROBID, to be used as potential training data for improvement.

**Resources:** 1-2 datanode VMs; hadoop cluster time. Needed up-front for
backlog processing; less CPU needed over time.

## Matchers

The matcher runs as a "scan" HBase map/reduce job over new (unprocessed) HBasej
rows. It pulls just the basic metadata (title, author, identifiers, abstract)
and calls the catalog API to identify potential match candidates. If no match
is found, and the metadata "look good" based on some filters (to remove, eg,
spam), works are inserted into the catalog (eg, for those works that don't have
globally available identifiers or other metadata; "long tail" and legacy
content).

**Resources:** Hadoop cluster time

## Catalog

The catalog is a versioned relational database. All scripts interact with an
API server (instead of connecting directly to the database). It should be
reliable and low-latency for simple reads, so it can be relied on to provide a
public-facing API and have public web interfaces built on top. This is in
contrast to Hadoop, which for the most part could go down with no public-facing
impact (other than fulltext API queries). The catalog does not contain
copywritable material, but it does contain strong (verified) links to fulltext
content. Policy gets implemented here if necessary.

A global "changelog" (append-only log) is used in the catalog to record every
change, allowing for easier replication (internal or external, to partners). As
little as possible is implemented in the catalog itself; instead helper and
cleanup bots use the API to propose and verify edits, similar to the wikidata
and git data models.

Public APIs and any front-end services are built on the catalog. Elasticsearch
(for metadata or fulltext search) could build on top of the catalog.

**Resources:** Unknown, but estimate 1+ TB of SSD storage each on 2 or more
database machines

## Machine Learning and "Bottom Up"

TBD.

## Logistics

Ansible is used to deploy all components. Luigi is used as a task scheduler for
batch jobs, with cron to initiate periodic tasks. Errors and actionable
problems are aggregated in Sentry.

Logging, metrics, and other debugging and monitoring are TBD.

