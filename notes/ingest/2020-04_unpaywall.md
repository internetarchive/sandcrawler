
A new snapshot was released in April 2020 (the snapshot is from 2020-02-25, but
not released for more than a month).

Primary goal is:

- generate ingest requests for only *new* URLs
- bulk ingest these new URLs
- crawl any no-capture URLs from that batch
- re-bulk-ingest the no-capture batch
- analytics on failed ingests. eg, any particular domains that are failing to crawl

This ingest pipeline was started on 2020-04-07 by bnewbold.

Ran through the first two steps again on 2020-05-03 after unpaywall had
released another dump (dated 2020-04-27).

## Transform and Load

    # in sandcrawler pipenv on aitio
    zcat /schnell/UNPAYWALL-PDF-CRAWL-2020-04/unpaywall_snapshot_2020-02-25T115244.jsonl.gz | ./scripts/unpaywall2ingestrequest.py - | pv -l > /grande/snapshots/unpaywall_snapshot_2020-02-25.ingest_request.json
    => 24.7M 5:17:03 [ 1.3k/s]

    cat /grande/snapshots/unpaywall_snapshot_2020-02-25.ingest_request.json | pv -l | ./persist_tool.py ingest-request -
    => 24.7M
    => Worker: Counter({'total': 24712947, 'insert-requests': 4282167, 'update-requests': 0})

Second time:

    # in sandcrawler pipenv on aitio
    zcat /schnell/UNPAYWALL-PDF-CRAWL-2020-04/unpaywall_snapshot_2020-04-27T153236.jsonl.gz | ./scripts/unpaywall2ingestrequest.py - | pv -l > /grande/snapshots/unpaywall_snapshot_2020-04-27.ingest_request.json
    => 25.2M 3:16:28 [2.14k/s]

    cat /grande/snapshots/unpaywall_snapshot_2020-04-27.ingest_request.json | pv -l | ./persist_tool.py ingest-request -
    => Worker: Counter({'total': 25189390, 'insert-requests': 1408915, 'update-requests': 0})
    => JSON lines pushed: Counter({'pushed': 25189390, 'total': 25189390})


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

    WARNING: forgot to transform from rows to ingest requests.

    cat /grande/snapshots/unpaywall_noingest_2020-04-08.rows.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

Second time:

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND date(ingest_request.created) > '2020-05-01'
            AND ingest_file_result.status IS NULL
    ) TO '/grande/snapshots/unpaywall_noingest_2020-05-03.rows.json';
    => 1799760

    WARNING: forgot to transform from rows to ingest requests.

    cat /grande/snapshots/unpaywall_noingest_2020-05-03.rows.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

## Dump no-capture, Run Crawl

Make two ingest request dumps: one with "all" URLs, which we will have heritrix
attempt to crawl, and then one with certain domains filtered out, which we may
or may not bother trying to ingest (due to expectation of failure).

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
    ) TO '/grande/snapshots/unpaywall_nocapture_all_2020-05-04.rows.json';
    => 2734145

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
    ) TO '/grande/snapshots/unpaywall_nocapture_2020-05-04.rows.json';
    => 2602408

NOTE: forgot here to transform from "rows" to ingest requests.

Not actually a very significant size difference after all.

See `journal-crawls` repo for details on seedlist generation and crawling.

## Re-Ingest Post-Crawl

NOTE: if we *do* want to do cleanup eventually, could look for fatcat edits
between 2020-04-01 and 2020-05-25 which have limited "extra" metadata (eg, no
evidence or `oa_status`).

The earlier bulk ingests were done wrong (forgot to transform from rows to full
ingest request docs), so going to re-do those, which should be a superset of
the nocapture crawl URLs.:

    ./scripts/ingestrequest_row2json.py /grande/snapshots/unpaywall_noingest_2020-04-08.rows.json | pv -l > /grande/snapshots/unpaywall_noingest_2020-04-08.json
    => 1.26M 0:00:58 [21.5k/s]
    => previously: 3,696,189

    ./scripts/ingestrequest_row2json.py /grande/snapshots/unpaywall_noingest_2020-05-03.rows.json | pv -l > /grande/snapshots/unpaywall_noingest_2020-05-03.json
    => 1.26M 0:00:56 [22.3k/s]

Crap, looks like the 2020-04-08 segment got overwriten with 2020-05 data by
accident. Hrm... need to re-ingest *all* recent unpaywall URLs:

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND date(ingest_request.created) > '2020-04-01'
    ) TO '/grande/snapshots/unpaywall_all_recent_requests_2020-05-26.rows.json';
    => COPY 5691106

    ./scripts/ingestrequest_row2json.py /grande/snapshots/unpaywall_all_recent_requests_2020-05-26.rows.json | pv -l | shuf > /grande/snapshots/unpaywall_all_recent_requests_2020-05-26.requests.json
    => 5.69M 0:04:26 [21.3k/s]
   
Start small:

    cat /grande/snapshots/unpaywall_all_recent_requests_2020-05-26.requests.json | head -n200 | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

Looks good (whew), run the full thing:

    cat /grande/snapshots/unpaywall_all_recent_requests_2020-05-26.requests.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1
