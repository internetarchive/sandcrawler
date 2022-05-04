
Another dump of PDF URLs for partners. This time want to provide TSV with full
wayback download URLs, as well as "access" URLs.

    export TASKDATE=2022-04-27

## "Ingested", AKA, "Targetted" PDF URLs

These are URLs where we did a successful ingest run.

    COPY (
        SELECT
            terminal_sha1hex as pdf_sha1hex,
            ('https://web.archive.org/web/' || terminal_dt || 'id_/' || terminal_url) as crawl_url,
            ('https://web.archive.org/web/' || terminal_dt || '/' || terminal_url) as display_url
        FROM ingest_file_result
        WHERE
            ingest_type = 'pdf'
            AND status = 'success'
            AND hit = true
        ORDER BY terminal_sha1hex ASC
        -- LIMIT 10;
    )
    TO '/srv/sandcrawler/tasks/ia_wayback_pdf_ingested.2022-04-27.tsv'
    WITH NULL '';
    => COPY 85712674

May contain duplicates, both by sha1hex, URL, or both.

Note that this could be filtered by timestamp, to make it monthly/annual.


## All CDX PDFs

"All web PDFs": CDX query; left join file_meta, but don't require

    COPY (
        SELECT
            cdx.sha1hex as pdf_sha1hex,
            ('https://web.archive.org/web/' || cdx.datetime || 'id_/' || cdx.url) as crawl_url,
            ('https://web.archive.org/web/' || cdx.datetime || '/' || cdx.url) as display_url
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
        ORDER BY cdx.sha1hex ASC
        -- LIMIT 10;
    )
    TO '/srv/sandcrawler/tasks/ia_wayback_pdf_speculative.2022-04-27.tsv'
    WITH NULL '';
    => COPY 161504070

Should be unique by wayback URL; may contain near-duplicates or duplicates by 

## Upload to archive.org

TODO: next time compress these files first (gzip/pigz)

ia upload ia_scholarly_urls_$TASKDATE \
    -m collection:ia_biblio_metadata \
    -m title:"IA Scholarly URLs ($TASKDATE)" \
    -m date:$TASKDATE \
    -m creator:"Internet Archive Web Group" \
    -m description:"URL lists to PDFs on the web (and preserved in the wayback machine) which are likely to contain research materials." \
    /srv/sandcrawler/tasks/ia_wayback_pdf_ingested.$TASKDATE.tsv /srv/sandcrawler/tasks/ia_wayback_pdf_speculative.$TASKDATE.tsv

