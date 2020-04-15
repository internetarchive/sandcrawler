
A new snapshot was released in April 2020 (the snapshot is from 2020-02-25, but
not released for more than a month).

Primary goal is:

- generate ingest requests for only *new* URLs
- bulk ingest these new URLs
- crawl any no-capture URLs from that batch
- re-bulk-ingest the no-capture batch
- analytics on failed ingests. eg, any particular domains that are failing to crawl

This ingest pipeline was started on 2020-04-07 by bnewbold.

## Transform and Load

    # in sandcrawler pipenv on aitio
    zcat /schnell/UNPAYWALL-PDF-CRAWL-2020-04/unpaywall_snapshot_2020-02-25T115244.jsonl.gz | ./scripts/unpaywall2ingestrequest.py - | pv -l > /grande/snapshots/unpaywall_snapshot_2020-02-25.ingest_request.json
    => 24.7M 5:17:03 [ 1.3k/s]

    cat /grande/snapshots/unpaywall_snapshot_2020-02-25.ingest_request.json | pv -l | ./persist_tool.py ingest-request -
    => 24.7M
    => Worker: Counter({'total': 24712947, 'insert-requests': 4282167, 'update-requests': 0})

## Dump new URLs and Bulk Ingest

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND date(ingest_request.created) > '2020-04-01'
            AND ingest_file_result.status IS NULL
    ) TO '/grande/snapshots/unpaywall_noingest_2020-04-08.rows.json';
    => 3696189

    cat /grande/snapshots/unpaywall_noingest_2020-04-08.rows.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

## Dump no-capture

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND date(ingest_request.created) > '2020-04-01'
            AND ingest_file_result.status = 'no-capture'
            AND ingest_request.base_url NOT LIKE '%journals.sagepub.com%'
            AND ingest_request.base_url NOT LIKE '%pubs.acs.org%'
            AND ingest_request.base_url NOT LIKE '%ahajournals.org%'
            AND ingest_request.base_url NOT LIKE '%www.journal.csj.jp%'
            AND ingest_request.base_url NOT LIKE '%aip.scitation.org%'
            AND ingest_request.base_url NOT LIKE '%academic.oup.com%'
            AND ingest_request.base_url NOT LIKE '%tandfonline.com%'
    ) TO '/grande/snapshots/unpaywall_nocapture_2020-04-XX.rows.json';
