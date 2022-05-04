
Want to dump a URL list to share with partners, filtered to content we think is
likely to be scholarly.

Columns to include:

- original URL
- capture timestamp
- SHA1

## Stats Overview

file_meta table, mimetype=application/pdf: 173,816,433

cdx table, mimetype=application/pdf: 131,346,703

ingest_file_result table, pdf, success: 66,487,928

## Ingested PDF URLs

"Ingested" URLs: ingest_file_result table, pdf and hit=true; include base URL also?

    COPY (
        SELECT
            base_url as start_url,
            terminal_url as pdf_url,
            terminal_dt as pdf_url_timestamp,
            terminal_sha1hex as pdf_sha1hex
        FROM ingest_file_result
        WHERE
            ingest_type = 'pdf'
            AND status = 'success'
    )
    TO '/srv/sandcrawler/tasks/wayback_pdf_targeted.2021-09-09.tsv'
    WITH NULL '';
    => 77,892,849

## CDX PDFs

"All web PDFs": CDX query; left join file_meta, but don't require

    COPY (
        SELECT
            cdx.url as pdf_url,
            cdx.datetime as pdf_url_timestamp,
            cdx.sha1hex as pdf_sha1hex
        FROM cdx
        LEFT JOIN file_meta
        ON
            cdx.sha1hex = file_meta.sha1hex
        WHERE
            file_meta.mimetype = 'application/pdf'
            OR (
                file_meta.mimetype IS NULL
                AND cdx.mimetype = 'application/pdf'
            )
    )
    TO '/srv/sandcrawler/tasks/wayback_pdf_speculative.2021-09-09.tsv'
    WITH NULL '';
    => 147,837,935

## Processed web PDFs

"Parsed web PDFs": `file_meta`, left join CDX

(didn't do this one)

---

Uploaded all these to <https://archive.org/download/ia_scholarly_urls_2021-09-09>
