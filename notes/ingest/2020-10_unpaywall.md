
New snapshot released 2020-10-09. Want to do a mostly straight-forward
load/ingest/crawl.

Proposed changes this time around:

- have bulk ingest store missing URLs in a new sandcrawler-db for `no-capture`
  status, and to include those URLs in heritrix3 crawl
- tweak heritrix3 config for additional PDF URL extraction patterns,
  particularly to improve OJS yield


## Transform and Load

    # in sandcrawler pipenv on aitio
    zcat /schnell/unpaywall/unpaywall_snapshot_2020-10-09T153852.jsonl.gz | ./scripts/unpaywall2ingestrequest.py - | pv -l > /grande/snapshots/unpaywall_snapshot_2020-10-09.ingest_request.json
    => 28.3M 3:19:03 [2.37k/s]

    cat /grande/snapshots/unpaywall_snapshot_2020-04-27.ingest_request.json | pv -l | ./persist_tool.py ingest-request -
    => 28.3M 1:11:29 [ 6.6k/s]
    => Worker: Counter({'total': 28298500, 'insert-requests': 4119939, 'update-requests': 0})
    => JSON lines pushed: Counter({'total': 28298500, 'pushed': 28298500})

## Dump new URLs, Transform, Bulk Ingest

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            -- AND date(ingest_request.created) > '2020-10-09'
            AND (ingest_file_result.status IS NULL
                OR ingest_file_result.status = 'no-capture')
    ) TO '/grande/snapshots/unpaywall_noingest_2020-10-09.rows.json';
    => COPY 4216339

    ./scripts/ingestrequest_row2json.py /grande/snapshots/unpaywall_noingest_2020-10-09.rows.json | pv -l | shuf > /grande/snapshots/unpaywall_noingest_2020-10-09.ingest_request.json
    => 4.22M 0:02:48 [  25k/s]

Start small, to test no-capture behavior:

    cat /grande/snapshots/unpaywall_noingest_2020-10-09.ingest_request.json | head -n1000 | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

`no-capture` change looks good. Enqueue the whole batch:

    cat /grande/snapshots/unpaywall_noingest_2020-10-09.ingest_request.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

Overall status after that:

    SELECT ingest_file_result.status, COUNT(*)
    FROM ingest_request
    LEFT JOIN ingest_file_result
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE 
        ingest_request.ingest_type = 'pdf'
        AND ingest_request.link_source = 'unpaywall'
    GROUP BY status
    ORDER BY COUNT DESC
    LIMIT 25;

                   status                |  count   
    -------------------------------------+----------
     success                             | 23661084
     no-capture                          |  3015448
     no-pdf-link                         |  2302092
     redirect-loop                       |  1542484
     terminal-bad-status                 |  1044654
     wrong-mimetype                      |   114315
     link-loop                           |    36357
     cdx-error                           |    20055
     null-body                           |    14513
     wayback-error                       |    14175
     gateway-timeout                     |     3747
     spn2-cdx-lookup-failure             |     1250
     petabox-error                       |     1171
     redirects-exceeded                  |      752
     invalid-host-resolution             |      464
     bad-redirect                        |      131
     spn2-error                          |      109
     spn2-error:job-failed               |       91
     timeout                             |       19
                                         |       13
     spn2-error:soft-time-limit-exceeded |        9
     bad-gzip-encoding                   |        6
     spn2-error:pending                  |        1
     skip-url-blocklist                  |        1
     pending                             |        1
    (25 rows)

## Crawl

Re-crawl broadly (eg, all URLs that have failed before, not just `no-capture`):

    COPY (
        SELECT row_to_json(r) FROM (
            SELECT ingest_request.*, ingest_file_result.terminal_url as terminal_url
            FROM ingest_request
            LEFT JOIN ingest_file_result
                ON ingest_file_result.ingest_type = ingest_request.ingest_type
                AND ingest_file_result.base_url = ingest_request.base_url
            WHERE
                ingest_request.ingest_type = 'pdf'
                AND ingest_request.ingest_request_source = 'unpaywall'
                AND ingest_file_result.status != 'success'
        ) r
    ) TO '/grande/snapshots/oa_doi_reingest_recrawl_20201014.rows.json';
    => 8111845

Hrm. Not sure how to feel about the no-pdf-link. Guess it is fine!

