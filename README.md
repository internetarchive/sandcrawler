
                                      _                         _           
    __________    ___  __ _ _ __   __| | ___ _ __ __ ___      _| | ___ _ __ 
    \         |  / __|/ _` | '_ \ / _` |/ __| '__/ _` \ \ /\ / / |/ _ \ '__|
     \        |  \__ \ (_| | | | | (_| | (__| | | (_| |\ V  V /| |  __/ |   
      \ooooooo|  |___/\__,_|_| |_|\__,_|\___|_|  \__,_| \_/\_/ |_|\___|_|   


This repo contains hadoop jobs, luigi tasks, and other scripts and code for the
internet archive web group's journal ingest pipeline.

Code in tihs repository is potentially public!

Archive-specific deployment/production guides and ansible scripts at:
[journal-infra](https://git.archive.org/webgroup/journal-infra)

**./python/** contains scripts and utilities for 

**./sql/** contains schema, queries, and backfill scripts for a Postgres SQL
database index (eg, file metadata, CDX, and GROBID status tables).

**./minio/** contains docs on how to setup and use a minio S3-compatible blob
store (eg, for GROBID XML output)

**./scalding/** contains Hadoop jobs written in Scala using the Scalding
framework. The intent is to write new non-trivial Hadoop jobs in Scala, which
brings type safety and compiled performance.

**./python_hadoop/** contains Hadoop streaming jobs written in python using the
`mrjob` library. Considered deprecated!

**./pig/** contains a handful of Pig scripts, as well as some unittests
implemented in python.

## Running Hadoop Jobs

The `./please` python3 wrapper script is a helper for running jobs (python or
scalding) on the IA Hadoop cluster. You'll need to run the setup/dependency
tasks first; see README files in subdirectories.

