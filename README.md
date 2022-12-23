
                                      _                         _           
    __________    ___  __ _ _ __   __| | ___ _ __ __ ___      _| | ___ _ __ 
    \         |  / __|/ _` | '_ \ / _` |/ __| '__/ _` \ \ /\ / / |/ _ \ '__|
     \        |  \__ \ (_| | | | | (_| | (__| | | (_| |\ V  V /| |  __/ |   
      \ooooooo|  |___/\__,_|_| |_|\__,_|\___|_|  \__,_| \_/\_/ |_|\___|_|   


This repo contains back-end python workers, scripts, config files, and other
stuff related to the Internet Archive web group's scholarly web preservation
and processing pipeline. It is a complement to [fatcat](https://fatcat.wiki),
which is an open catalog of research outputs, including preservation metadata.

The sandcrawler part of the project deals with content crawled from the web
into either web.archive.org or archive.org collections, and post-processing
that content. For example, extracting text from PDF files, verifying mimetypes,
and checking archival status. The resulting metadata ends up getting filtered,
transformed, and pushed in to fatcat itself for public use.

While code in this repository is public, it is mostly IA-specific and may not
even run outside the IA data centers due to library dependencies and
authentication needs. Code quality and documentation is generally poor compared
to fatcat.

As of December 2022, the best document to read for "getting started" in
understanding the ingest system is `proposals/2019_ingest.md`, and then
subsequent proposals expanding on that foundation.

Archive-specific deployment/production guides and ansible scripts at:
[journal-infra](https://git.archive.org/webgroup/journal-infra)


## Repository Layout

**./python/** contains scripts and utilities for ingesting content from wayback
and/or the web (via save-page-now API), and other processing pipelines. Most of
the active code is in here. See included README (`./python/README.md`)

**./sql/** contains schema, queries, and backfill scripts for a Postgres SQL
database index (eg, file metadata, CDX, and GROBID status tables).

**./python_hadoop/** contains Hadoop streaming jobs written in python using the
`mrjob` library. Still use the HBase backfill code path occasionally.

**./proposals/** design documentation and change proposals

**./notes/ingest/** log of bulk crawls and metadata loads

**./extra/docker/** docker-compose setup that may be useful for documentation
(includes Kafka, PostgreSQL, etc)

**./.gitlab-ci.yml** current CI setup script, which documents dependencies

**./pig/** contains a handful of Pig scripts, as well as some unittests
implemented in python. Only rarely used.

**./scalding/** contains Hadoop jobs written in Scala using the Scalding
framework. The intent is to write new non-trivial Hadoop jobs in Scala, which
brings type safety and compiled performance. Mostly DEPRECATED, this code has
not been run in years.


## Running Python Hadoop Jobs

The `./please` python3 wrapper script is a helper for running jobs (python or
scalding) on the IA Hadoop cluster. You'll need to run the setup/dependency
tasks first; see README files in subdirectories.
