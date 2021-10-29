
GROBID References in Sandcrawler DB
===================================

Want to start processing "unstructured" raw references coming from upstream
metadata sources (distinct from upstream fulltext sources, like PDFs or JATS
XML), and save the results in sandcrawler DB. From there, they will get pulled
in to fatcat-scholar "intermediate bundles" and included in reference exports.

The initial use case for this is to parse "unstructured" references deposited
in Crossref, and include them in refcat.


## Schema and Semantics

Follows that of `grobid_tei_xml` version 0.1.

Not all references are necessarily included for GROBID processing. They should
identified and mapped using the entire unstructured string.

When present, `key` or `id` is woven back in to the ref objects (GROBID
`processCitationList` doesn't ever see the keys). `index`, returned by
`grobid_tei_xml`, may not be accurate (because not all references were passed),
and may be removed (TBD).


## New SQL Table and View

    CREATE TABLE IF NOT EXISTS grobid_refs (
        source              TEXT NOT NULL CHECK (octet_length(source) >= 1),
        source_id           TEXT NOT NULL CHECK (octet_length(source_id) >= 1),
        source_ts           TIMESTAMP WITH TIME ZONE,
        updated             TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        refs_json           JSONB NOT NULL,
        PRIMARY KEY(source, source_id)
    );

    CREATE OR REPLACE VIEW crossref_with_refs
        doi, indexed, record, source_ts, refs_json AS
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
