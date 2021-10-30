
GROBID References in Sandcrawler DB
===================================

Want to start processing "unstructured" raw references coming from upstream
metadata sources (distinct from upstream fulltext sources, like PDFs or JATS
XML), and save the results in sandcrawler DB. From there, they will get pulled
in to fatcat-scholar "intermediate bundles" and included in reference exports.

The initial use case for this is to parse "unstructured" references deposited
in Crossref, and include them in refcat.


## Schema and Semantics

The output JSON/dict schema for parsed references follows that of
`grobid_tei_xml` version 0.1.x, for the `GrobidBiblio` field. The
`unstructured` field that was parsed is included in the output, though it may
not be byte-for-byte exact (see below). One notable change from the past (eg,
older GROBID-parsed references) is that author `name` is now `full_name`. New
fields include `editors` (same schema as `authors`), `book_title`, and
`series_title`.

The overall output schema matches that of the `grobid_refs` SQL table:

    source: string, lower-case. eg 'crossref'
    source_id: string, eg '10.1145/3366650.3366668'
    source_ts: optional timestamp (full ISO datetime with timezone (eg, `Z`
               suffix), which identifies version of upstream metadata
    refs_json: JSONB, list of `GrobidBiblio` JSON objects

References are re-processed on a per-article (or per-release) basis. All the
references for an article are handled as a batch and output as a batch. If
there are no upstream references, row with `ref_json` as empty list may be
returned.

Not all upstream references get re-parsed, even if an 'unstructured' field is
available. If 'unstructured' is not available, no row is ever output. For
example, if a reference includes `unstructured` (raw citation string), but also
has structured metadata for authors, title, year, and journal name, we might
not re-parse the `unstructured` string. Whether to re-parse is evaulated on a
per-reference basis. This behavior may change over time.

`unstructured` strings may be pre-processed before being submitted to GROBID.
This is because many sources have systemic encoding issues. GROBID itself may
also do some modification of the input citation string before returning it in
the output. This means the `unstructured` string is not a reliable way to map
between specific upstream references and parsed references. Instead, the `id`
field (str) of `GrobidBiblio` gets set to any upstream "key" or "index"
identifier used to track individual references. If there is only a numeric
index, the `id` is that number as a string.

The `key` or `id` may need to be woven back in to the ref objects manually,
because GROBID `processCitationList` takes just a list of raw strings, with no
attached reference-level key or id.


## New SQL Table and View

We may want to do re-parsing of references from sources other than `crossref`,
so there is a generic `grobid_refs` table. But it is also common to fetch both
the crossref metadata and any re-parsed references together, so as a convience
there is a PostgreSQL view (virtual table) that includes both a crossref
metadata record and parsed citations, if available. If downstream code cares a
lot about having the refs and record be in sync, the `source_ts` field on
`grobid_refs` can be matched againt the `indexed` column of `crossref` (or the
`.indexed.date-time` JSON field in the record itself).

Remember that DOIs should always be lower-cased before querying, inserting,
comparing, etc.

    CREATE TABLE IF NOT EXISTS grobid_refs (
        source              TEXT NOT NULL CHECK (octet_length(source) >= 1),
        source_id           TEXT NOT NULL CHECK (octet_length(source_id) >= 1),
        source_ts           TIMESTAMP WITH TIME ZONE,
        updated             TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        refs_json           JSONB NOT NULL,
        PRIMARY KEY(source, source_id)
    );

    CREATE OR REPLACE VIEW crossref_with_refs (doi, indexed, record, source_ts, refs_json) AS
        SELECT
            crossref.doi as doi,
            crossref.indexed as indexed,
            crossref.record as record,
            grobid_refs.source_ts as source_ts,
            grobid_refs.refs_json as refs_json
        FROM crossref
        LEFT JOIN grobid_refs ON
            grobid_refs.source_id = crossref.doi
            AND grobid_refs.source = 'crossref';

Both `grobid_refs` and `crossref_with_refs` will be exposed through postgrest.


## New Workers / Tools

For simplicity, to start, a single worker with consume from
`fatcat-prod.api-crossref`, process citations with GROBID (if necessary), and
insert to both `crossref` and `grobid_refs` tables. This worker will run
locally on the machine with sandcrawler-db.

Another tool will support taking large chunks of Crossref JSON (as lines),
filter them, process with GROBID, and print JSON to stdout, in the
`grobid_refs` JSON schema.


## Task Examples

Command to process crossref records with refs tool:

    cat crossref_sample.json \
        | parallel -j5 --linebuffer --round-robin --pipe ./grobid_tool.py parse-crossref-refs - \
        | pv -l \
        > crossref_sample.parsed.json

    # => 10.0k 0:00:27 [ 368 /s]

Load directly in to postgres (after tables have been created):

    cat crossref_sample.parsed.json \
        | jq -rc '[.source, .source_id, .source_ts, (.refs_json | tostring)] | @tsv' \
        | psql sandcrawler -c "COPY grobid_refs (source, source_id, source_ts, refs_json) FROM STDIN (DELIMITER E'\t');"

    # => COPY 9999
