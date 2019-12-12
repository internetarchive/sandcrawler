
status: brainstorming/backburner

last updated: 2019-12-11

This document proposes changes to extract text and metadata from PDFs at ingest
time using pdftotext and pdfinfo, and storing this content in SQL and minio.

This isn't a priority at the moment. Could be useful for fulltext search when
GROBID fails, and the pdfinfo output might help with other quality checks.

## Overview / Motivation

`pdfinfo` and `pdftotext` can both be run quickly over raw PDFs. In
sandcrawler, fetching PDFs can be a bit slow, so the motivation for caching the
text is just to not have to fetch the PDFs over and over. Metadata is useful to
store and index at scale.

## pdfinfo output

Example PDF info outputs:

    Creator:        PDF Suite 2010
    Producer:       PDF Suite 2010
    CreationDate:   Tue Sep 24 23:03:58 2013 PDT
    ModDate:        Tue Sep 24 23:03:58 2013 PDT
    Tagged:         no
    UserProperties: no
    Suspects:       no
    Form:           none
    JavaScript:     no
    Pages:          17
    Encrypted:      no
    Page size:      612 x 792 pts (letter)
    Page rot:       0
    File size:      105400 bytes
    Optimized:      no
    PDF version:    1.4

another:

    Title:          Miscellanea Zoologica Hungarica 8. 1993 (Budapest, 1993)
    Author:         L. Forró szerk.
    Producer:       ABBYY FineReader 9.0 Corporate Edition
    CreationDate:   Wed Apr 13 05:30:21 2011 PDT
    ModDate:        Wed Apr 13 09:53:27 2011 PDT
    Tagged:         yes
    UserProperties: no
    Suspects:       no
    Form:           AcroForm
    JavaScript:     no
    Pages:          13
    Encrypted:      no
    Page size:      473.76 x 678.42 pts
    Page rot:       0
    File size:      12047270 bytes
    Optimized:      no
    PDF version:    1.6

With the `-meta` flag, you get XML output, which also includes:

    <xmpMM:DocumentID>uuid:cd1a8daa-61e1-48f4-b679-26eac52bb6a9</xmpMM:DocumentID>
    <xmpMM:InstanceID>uuid:dea54c78-8bc6-4f2f-a665-4cd7e62457e7</xmpMM:InstanceID>

The document id is particularly interesting for fatcat/sandcrawler. Apparently
it is randomly created (or based on md5?) of first version of the file, and
persists across edits. A quality check would be that all files with the same
`document_id` should be clustered under the same fatcat work.

All the info fields could probably be combined and used in categorization and
filtering (ML or heuristic). Eg, a PDF with forms is probably not research
output; published PDFs with specific "Producer" software probably are.

## Fatcat Changes

Could include in entity fields, a `pdfinfo` JSONB field, or existing `extra`:

- pages
- words
- document id
- page size
- created
- other meta (eg, PDF title, author, etc)

All of these fields are, I assume, deterministic, thus appropriate for
inclusion in fatcat.

## New SQL Tables

    CREATE TABLE IF NOT EXISTS pdftotext (
        sha1hex             TEXT PRIMARY KEY CHECK (octet_length(sha1hex) = 40),
        updated             TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        tool_version        TEXT CHECK (octet_length(tool_version) >= 1),
        text_success        BOOLEAN NOT NULL,
        text_words          INT,
        info_success        BOOLEAN NOT NULL,
        pages               INT,
        pdf_created         TIMESTAMP WITH TIME ZONE,
        document_id         TEXT CHECK (octet_length(document_id) >= 1), -- XXX: always UUID?
        metadata            JSONB
        -- metadata contains any other stuff from pdfinfo:
        --  title
        --  author
        --  pdf version
        --  page size (?)
        --  instance_id
    );
    -- CREATE INDEX pdftotext ON pdftotext(document_id);

## New Kafka Topics

    sandcrawler-ENV.pdftotext-output

Key would be sha1hex of PDF.

Schema would match the SQL table, plus the full raw PDF text output.

## New Minio Stuff

    /pdftotext/<hexbyte0>/<hexbyte1>/<sha1hex>.txt

## Open Questions

