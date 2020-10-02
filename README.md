
                                      _                         _           
    __________    ___  __ _ _ __   __| | ___ _ __ __ ___      _| | ___ _ __ 
    \         |  / __|/ _` | '_ \ / _` |/ __| '__/ _` \ \ /\ / / |/ _ \ '__|
     \        |  \__ \ (_| | | | | (_| | (__| | | (_| |\ V  V /| |  __/ |   
      \ooooooo|  |___/\__,_|_| |_|\__,_|\___|_|  \__,_| \_/\_/ |_|\___|_|   


This repo contains back-end python workers, scripts, hadoop jobs, luigi tasks,
and other scripts and code for the Internet Archive web group's journal ingest
pipeline. This code is of mixed quality and is mostly experimental. The goal
for most of this is to submit metadata to [fatcat](https://fatcat.wiki), which
is the more stable, maintained, and public-facing service.

Code in this repository is potentially public! Not intented to accept public
contributions for the most part. Much of this will not work outside the IA
cluster environment.

Archive-specific deployment/production guides and ansible scripts at:
[journal-infra](https://git.archive.org/webgroup/journal-infra)


## Repository Layout

**./proposals/** design documentation and change proposals

**./python/** contains scripts and utilities for ingesting content from wayback
and/or the web (via save-page-now API), and other processing pipelines

**./sql/** contains schema, queries, and backfill scripts for a Postgres SQL
database index (eg, file metadata, CDX, and GROBID status tables).

**./pig/** contains a handful of Pig scripts, as well as some unittests
implemented in python. Only rarely used.

**./scalding/** contains Hadoop jobs written in Scala using the Scalding
framework. The intent is to write new non-trivial Hadoop jobs in Scala, which
brings type safety and compiled performance. Mostly DEPRECATED.

**./python_hadoop/** contains Hadoop streaming jobs written in python using the
`mrjob` library. Mostly DEPRECATED.


## Running Python Code

You need python3.7 (or python3.6+ and `pyenv`) and `pipenv` to set up the
environment. You may also need the debian packages `libpq-dev` and `
`python-dev` to install some dependencies.


## Running Hadoop Jobs (DEPRECATED)

The `./please` python3 wrapper script is a helper for running jobs (python or
scalding) on the IA Hadoop cluster. You'll need to run the setup/dependency
tasks first; see README files in subdirectories.
