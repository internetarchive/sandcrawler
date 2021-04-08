
TL;DR: replace hbase with postgresql tables with REST API (http://postgrest.org)

No primary storage of anything in this table. Everything should be rapidly
re-creatable from dumps, kafka topics (compressed), CDX, petabox metadata, etc.
This is a secondary view on all of that.

## Create Database and User

Create system user with your username like:

    sudo su postgres
    createuser -s bnewbold

Create database using `diesel` tool (see fatcat rust docs for install notes):

    # DANGER: will delete/recreate entire database
    diesel database reset

In the future would probably be better to create a real role/password and
supply these via `DATABASE_URL` env variable.

## Schema

    schema/database name is 'sandcrawler'

    cdx: include revisits or not?
        id: int64, PK
        sha1hex: string, not null, index
        cdx_sha1hex: string
        url: string, not null
        datetime: ISO 8601:1988 (string?), not null
        mimetype: string
        warc_path: string (item and filename)
        warc_offset: i64
        created: datetime, index (?)
       ?crawl: string
       ?domain: string

    file_meta
        sha1hex, string, PK
        md5hex: string
        sha256hex: string
        size_bytes: i64
        mime: string (verifying file status; optional for now?)

    fatcat_file
        sha1hex: string, PK
        file_ident: string, index?
        release_ident: ?

    petabox
        id: int64, PK
        sha1hex: string, notnull, index
        item: string, notnull
        path: string, notnull (TODO: URL encoded? separate sub-archive path?)

    grobid
        sha1hex: string, PK
        updated: datetime
        grobid_version (string)
        status_code: i32
        status: string (JSONB?), only if status != 200
        metadata: JSONB, title, first author, year (not for now?)
        glutton_fatcat_release: string, index

    shadow
        sha1hex: string, PK
        shadow_corpus: string, PK
        shadow_id: string
        doi: string
        pmid: string
        isbn13: string

Alternatively, to be more like existing system could have "one big table" or
multiple tables all with same key (sha1b32) and UNIQ. As is, every sha1 pk
column is 40 bytes of both index and data, or 8+ GByte (combined) for each
table with 100 million rows. using raw bytes could help, but makes all
code/queries much trickier.

Should we have "created" or "updated" timestamps on all these columns to enable
kafka tailing?

TODO:
- how to indicate CDX sha1 vs. true sha1 mis-match? pretty rare. recrawl and delete row from `gwb_cdx`?
- only most recent GROBID? or keep multiple versions? here and minio

## Existing Stuff Sizes (estimates)

     78.5G  /user/bnewbold/journal_crawl_cdx
     19.7G  /user/bnewbold/sandcrawler/output-prod/2018-12-14-1737.00-dumpfilemeta
      2.7G  file_hashes.tsv
    228.5G  /user/bnewbold/sandcrawler/output-prod/2018-09-23-0405.30-dumpgrobidmetainsertable

## Use Cases

Core goal here is to mostly kill hbase/hadoop. What jobs are actually used there?

- backfill: load in-scope (fulltext) crawl results from CDX
    => bulk (many line) inserts
- rowcount: "how many unique PDFs crawled?"
    => trivial SQL query
- status code count: "how much GROBID progress?"
    => trivial SQL query
- dumpungrobided: "what files still need to be processed"
    => SQL join with a "first" on CDX side
- dumpgrobidxml: "merge CDX/file info with extracted XML, for those that were successful"
    => SQL dump or rowscan, then minio fetches

This table is generally "single file raw fulltext metadata".

"Enrichment" jobs:

- GROBID
- glutton (if not GROBID)
- extra file metadata
- match newly enriched files to fatcat

What else?

- track additional raw file metadata
- dump all basic GROBID metadata (title, authors, year) to attempt merge/match

Questions we might want to answer

- total size of PDF corpus (terabytes)
- unqiue files hit per domain

## Prototype Plan

- backfill all CDX crawl files (TSV transform?)
- load full GROBID XML (both into minio and into SQL)
- load full fatcat file dump (TSV transform)
- load dumpfilemeta

## Example Useful Lookups


    http get :3030/cdx?url=eq.https://coleccionables.mercadolibre.com.ar/arduino-pdf_Installments_NoInterest_BestSellers_YES
    http get :3030/file_meta?sha1hex=eq.120582c855a7cc3c70a8527c560d7f27e6027278


## Full SQL Database Dumps

Run a dump in compressed, postgres custom format:

    export DATESLUG="`date +%Y-%m-%d.%H%M%S`"
    time sudo -u postgres pg_dump --verbose --format=custom sandcrawler > sandcrawler_full_dbdump_${DATESLUG}.pgdump

As of 2021-04-07, this process runs for about 4 hours and the compressed
snapshot is 88 GBytes (compared with 551.34G database disk consumption).
