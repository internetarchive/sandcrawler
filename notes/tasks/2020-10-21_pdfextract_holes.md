
Realized I had not enabled persisting of PDF extraction results (thumbnail,
text) in ingest worker when added over the summer. So now need to run a
catch-up. This applied to both "live" and "bulk" ingest.

## `cdx` / `ingest` / `grobid` catch-up

First, re-run extraction for cases where we did an ingest, and grobid ran
successfully, and we have a CDX row, but no `pdf_meta`:

    -- this is a slow query
    COPY (
      SELECT DISTINCT ON (cdx.sha1hex) row_to_json(cdx)
      FROM grobid
      LEFT JOIN cdx ON grobid.sha1hex = cdx.sha1hex
      --LEFT JOIN fatcat_file ON grobid.sha1hex = fatcat_file.sha1hex
      LEFT JOIN ingest_file_result ON grobid.sha1hex = ingest_file_result.terminal_sha1hex
      LEFT JOIN pdf_meta ON grobid.sha1hex = pdf_meta.sha1hex
      WHERE cdx.sha1hex IS NOT NULL
        --AND fatcat_file.sha1hex IS NOT NULL
        AND ingest_file_result.terminal_sha1hex IS NOT NULL
        AND pdf_meta.sha1hex IS NULL
    )
    TO '/grande/snapshots/dump_unextracted_pdf.ingest.2020-10-21.json'
    WITH NULL '';
    => 19,676,116

Wow, that is a lot. Many from recent OAI-PMH and OA crawls, presumably.

    cat /grande/snapshots/dump_unextracted_pdf.ingest.2020-10-21.json | rg -v "\\\\" | jq . -c | pv -l | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.unextracted -p -1

And again, after a couple partitions got hung up:

    COPY (
      SELECT DISTINCT ON (cdx.sha1hex) row_to_json(cdx)
      FROM grobid
      LEFT JOIN cdx ON grobid.sha1hex = cdx.sha1hex
      --LEFT JOIN fatcat_file ON grobid.sha1hex = fatcat_file.sha1hex
      LEFT JOIN ingest_file_result ON grobid.sha1hex = ingest_file_result.terminal_sha1hex
      LEFT JOIN pdf_meta ON grobid.sha1hex = pdf_meta.sha1hex
      WHERE cdx.sha1hex IS NOT NULL
        --AND fatcat_file.sha1hex IS NOT NULL
        AND ingest_file_result.terminal_sha1hex IS NOT NULL
        AND pdf_meta.sha1hex IS NULL
    )
    TO '/grande/snapshots/dump_unextracted_pdf.ingest.2020-11-04.json'
    WITH NULL '';


    cat /grande/snapshots/dump_unextracted_pdf.ingest.2020-11-04.json | rg -v "\\\\" | jq . -c | pv -l | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.unextracted -p -1
    => 562k 0:00:16 [34.6k/s]

## `petabox` / `grobid` catch-up

These didn't all seem to extract correctly before after 1.5m rows, there will
still 900k unprocessed. Trying again.

    COPY (
      SELECT DISTINCT ON (petabox.sha1hex) row_to_json(petabox)
      FROM grobid
      LEFT JOIN petabox ON grobid.sha1hex = petabox.sha1hex
      LEFT JOIN pdf_meta ON grobid.sha1hex = pdf_meta.sha1hex
      WHERE petabox.sha1hex IS NOT NULL
        AND pdf_meta.sha1hex IS NULL
    )
    TO '/grande/snapshots/dump_unextracted_pdf_petabox.2020-11-04.json'
    WITH NULL '';

    cat /grande/snapshots/dump_unextracted_pdf_petabox.ingest.2020-11-04.json | rg -v "\\\\" | jq . -c | pv -l | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.unextracted -p -1

## `cdx` / `grobid` catch-up

Next will be to process PDFs with GROBID and CDX but no ingest.

