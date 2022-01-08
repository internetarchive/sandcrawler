
Martin crawled more than 10 million new PDFs from various platform domains. We
should get these processed and included in sandcrawler-db.

## Select CDX Rows

    COPY (
        SELECT DISTINCT ON (cdx.sha1hex) row_to_json(cdx)
        FROM cdx
        LEFT JOIN grobid ON grobid.sha1hex = cdx.sha1hex
        WHERE
            grobid.sha1hex IS NULL
            AND cdx.sha1hex IS NOT NULL
            AND cdx.warc_path LIKE 'PLATFORM-CRAWL-2020%'
        -- LIMIT 5;
    )
    TO '/srv/sandcrawler/tasks/ungrobided_platform_crawl.2022-01-07.cdx.json'
    WITH NULL '';
    => COPY 8801527

    cat /srv/sandcrawler/tasks/ungrobided_platform_crawl.2022-01-07.cdx.json | rg -v "\\\\" | jq . -c | pv -l | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ungrobided-pg -p -1

    # for pdfextract, would be: sandcrawler-prod.unextracted
