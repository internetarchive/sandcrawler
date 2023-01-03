
status: deployed

Crossref DOI Metadata in Sandcrawler DB
=======================================

Proposal is to have a local copy of Crossref API metadata records in
sandcrawler DB, accessible by simple key lookup via postgrest.

Initial goal is to include these in scholar work "bundles" (along with
fulltext, etc), in particular as part of reference extraction pipeline. Around
late 2020, many additional references became available via Crossref records,
and have not been imported (updated) into fatcat. Reference storage in fatcat
API is a scaling problem we would like to put off, so injecting content in this
way is desirable.

To start, working with a bulk dump made available by Crossref. In the future,
might persist the daily feed to that we have a continuously up-to-date copy.

Another application of Crossref-in-bundles is to identify overall scale of
changes since initial Crossref metadata import.


## Sandcrawler DB Schema

The "updated" field in this case refers to the upstream timestamp, not the
sandcrawler database update time.

    CREATE TABLE IF NOT EXISTS crossref (
        doi                 TEXT NOT NULL CHECK (octet_length(doi) >= 4 AND doi = LOWER(doi)),
        indexed             TIMESTAMP WITH TIME ZONE NOT NULL,
        record              JSON NOT NULL,
        PRIMARY KEY(doi)
    );

For postgrest access, may need to also:

    GRANT SELECT ON public.crossref TO web_anon;

## SQL Backfill Command

For an example file:

    cat sample.json \
        | jq -rc '[(.DOI | ascii_downcase), .indexed."date-time", (. | tostring)] | @tsv' \
        | psql sandcrawler -c "COPY crossref (doi, indexed, record) FROM STDIN (DELIMITER E'\t');"

For a full snapshot:

    zcat crossref_public_data_file_2021_01.json.gz \
        | pv -l \
        | jq -rc '[(.DOI | ascii_downcase), .indexed."date-time", (. | tostring)] | @tsv' \
        | psql sandcrawler -c "COPY crossref (doi, indexed, record) FROM STDIN (DELIMITER E'\t');"

jq is the bottleneck (100% of a single CPU core).

## Kafka Worker

Pulls from the fatcat crossref ingest Kafka feed and persists into the crossref
table.

## SQL Table Disk Utilization

An example backfill from early 2021, with about 120 million Crossref DOI
records.

Starting database size (with ingest running):

    Filesystem      Size  Used Avail Use% Mounted on
    /dev/vdb1       1.7T  896G  818G  53% /1

    Size: 475.14G

Ingest SQL command took:

    120M 15:06:08 [2.22k/s]
    COPY 120684688

After database size:

    Filesystem      Size  Used Avail Use% Mounted on
    /dev/vdb1       1.7T  1.2T  498G  71% /1

    Size: 794.88G

So about 320 GByte of disk.
