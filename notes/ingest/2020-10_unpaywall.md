
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


## Check Pre-Crawl Status

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
    LIMIT 20;


             status          |  count   
    -------------------------+----------
     success                 | 23661282
     no-capture              |  3015447
     no-pdf-link             |  2302102
     redirect-loop           |  1542566
     terminal-bad-status     |  1044676
     wrong-mimetype          |   114315
     link-loop               |    36358
     cdx-error               |    20150
     null-body               |    14513
     wayback-error           |    13644
     gateway-timeout         |     3776
     spn2-cdx-lookup-failure |     1260
     petabox-error           |     1171
     redirects-exceeded      |      752
     invalid-host-resolution |      464
     spn2-error              |      147
     bad-redirect            |      131
     spn2-error:job-failed   |       91
     wayback-content-error   |       45
     timeout                 |       19
    (20 rows)

## Dump Seedlist

Dump rows:

    COPY (
        SELECT row_to_json(t1.*)
        FROM (
            SELECT ingest_request.*, ingest_file_result as result
            FROM ingest_request
            LEFT JOIN ingest_file_result
                ON ingest_file_result.ingest_type = ingest_request.ingest_type
                AND ingest_file_result.base_url = ingest_request.base_url
            WHERE
                ingest_request.ingest_type = 'pdf'
                AND ingest_request.link_source = 'unpaywall'
                AND (ingest_file_result.status = 'no-capture'
                    OR ingest_file_result.status = 'cdx-error'
                    OR ingest_file_result.status = 'wayback-error'
                    OR ingest_file_result.status = 'gateway-timeout'
                    OR ingest_file_result.status = 'spn2-cdx-lookup-failure'
                )
                AND ingest_request.base_url NOT LIKE '%journals.sagepub.com%'
                AND ingest_request.base_url NOT LIKE '%pubs.acs.org%'
                AND ingest_request.base_url NOT LIKE '%ahajournals.org%'
                AND ingest_request.base_url NOT LIKE '%www.journal.csj.jp%'
                AND ingest_request.base_url NOT LIKE '%aip.scitation.org%'
                AND ingest_request.base_url NOT LIKE '%academic.oup.com%'
                AND ingest_request.base_url NOT LIKE '%tandfonline.com%'
                AND ingest_file_result.terminal_url NOT LIKE '%journals.sagepub.com%'
                AND ingest_file_result.terminal_url NOT LIKE '%pubs.acs.org%'
                AND ingest_file_result.terminal_url NOT LIKE '%ahajournals.org%'
                AND ingest_file_result.terminal_url NOT LIKE '%www.journal.csj.jp%'
                AND ingest_file_result.terminal_url NOT LIKE '%aip.scitation.org%'
                AND ingest_file_result.terminal_url NOT LIKE '%academic.oup.com%'
                AND ingest_file_result.terminal_url NOT LIKE '%tandfonline.com%'
        ) t1
    ) TO '/grande/snapshots/unpaywall_seedlist_2020-11-02.rows.json';
    => 2,936,404

    # TODO: in the future also exclude "www.archive.org"

Prep ingest requests (for post-crawl use):

    ./scripts/ingestrequest_row2json.py /grande/snapshots/unpaywall_seedlist_2020-11-02.rows.json | pv -l > /grande/snapshots/unpaywall_crawl_ingest_2020-11-02.json

And actually dump seedlist(s):

    cat /grande/snapshots/unpaywall_seedlist_2020-11-02.rows.json | jq -r .base_url | sort -u -S 4G > /grande/snapshots/unpaywall_seedlist_2020-11-02.url.txt
    cat /grande/snapshots/unpaywall_seedlist_2020-11-02.rows.json | rg '"no-capture"' | jq -r .result.terminal_url | rg -v ^null$ | sort -u -S 4G > /grande/snapshots/unpaywall_seedlist_2020-11-02.terminal_url.txt
    cat /grande/snapshots/unpaywall_seedlist_2020-11-02.rows.json | rg -v '"no-capture"' | jq -r .base_url | sort -u -S 4G > /grande/snapshots/unpaywall_seedlist_2020-11-02.no_terminal_url.txt

    wc -l unpaywall_seedlist_2020-11-02.*.txt
     2701178 unpaywall_seedlist_2020-11-02.terminal_url.txt
     2713866 unpaywall_seedlist_2020-11-02.url.txt

With things like jsessionid, suspect that crawling just the terminal URLs is
going to work better than both full and terminal.

Finding a fraction of `no-capture` which have partial/stub URLs as terminal.

TODO: investigate scale of partial/stub `terminal_url` (eg, not HTTP/S or FTP).


## Bulk Ingest and Status

Note, removing archive.org links:

    cat /grande/snapshots/unpaywall_crawl_ingest_2020-11-02.json | rg -v www.archive.org | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

Overall status (checked 2020-12-08):

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
        LIMIT 20;

             status          |  count   
    -------------------------+----------
     success                 | 25004559
     no-pdf-link             |  2531841
     redirect-loop           |  1671375
     terminal-bad-status     |  1389463
     no-capture              |   893880
     wrong-mimetype          |   119332
     link-loop               |    66508
     wayback-content-error   |    30339
     cdx-error               |    21790
     null-body               |    20710
     wayback-error           |    13976
     gateway-timeout         |     3775
     petabox-error           |     2420
     spn2-cdx-lookup-failure |     1218
     redirects-exceeded      |      889
     invalid-host-resolution |      464
     bad-redirect            |      147
     spn2-error              |      112
     spn2-error:job-failed   |       91
     timeout                 |       21
    (20 rows)

Ingest stats broken down by publication stage:

    SELECT ingest_request.release_stage, ingest_file_result.status, COUNT(*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
        GROUP BY release_stage, status
        ORDER BY release_stage, COUNT DESC
        LIMIT 100;


     release_stage |               status                |  count
    ---------------+-------------------------------------+----------
     accepted      | success                             |  1101090
     accepted      | no-pdf-link                         |    28590
     accepted      | redirect-loop                       |    10923
     accepted      | no-capture                          |     9540
     accepted      | terminal-bad-status                 |     6339
     accepted      | cdx-error                           |      952
     accepted      | wrong-mimetype                      |      447
     accepted      | link-loop                           |      275
     accepted      | wayback-error                       |      202
     accepted      | petabox-error                       |      177
     accepted      | redirects-exceeded                  |      122
     accepted      | null-body                           |       27
     accepted      | wayback-content-error               |       14
     accepted      | spn2-cdx-lookup-failure             |        5
     accepted      | gateway-timeout                     |        4
     accepted      | bad-redirect                        |        1
     published     | success                             | 18595278
     published     | no-pdf-link                         |  2434935
     published     | redirect-loop                       |  1364110
     published     | terminal-bad-status                 |  1185328
     published     | no-capture                          |   718792
     published     | wrong-mimetype                      |   112923
     published     | link-loop                           |    63874
     published     | wayback-content-error               |    30268
     published     | cdx-error                           |    17302
     published     | null-body                           |    15209
     published     | wayback-error                       |    10782
     published     | gateway-timeout                     |     1966
     published     | petabox-error                       |     1611
     published     | spn2-cdx-lookup-failure             |      879
     published     | redirects-exceeded                  |      760
     published     | invalid-host-resolution             |      453
     published     | bad-redirect                        |      115
     published     | spn2-error:job-failed               |       77
     published     | spn2-error                          |       75
     published     | timeout                             |       21
     published     | bad-gzip-encoding                   |        5
     published     | spn2-error:soft-time-limit-exceeded |        4
     published     | spn2-error:pending                  |        1
     published     | blocked-cookie                      |        1
     published     |                                     |        1
     published     | pending                             |        1
     submitted     | success                             |  5308166
     submitted     | redirect-loop                       |   296322
     submitted     | terminal-bad-status                 |   197785
     submitted     | no-capture                          |   165545
     submitted     | no-pdf-link                         |    68274
     submitted     | wrong-mimetype                      |     5962
     submitted     | null-body                           |     5474
     submitted     | cdx-error                           |     3536
     submitted     | wayback-error                       |     2992
     submitted     | link-loop                           |     2359
     submitted     | gateway-timeout                     |     1805
     submitted     | petabox-error                       |      632
     submitted     | spn2-cdx-lookup-failure             |      334
     submitted     | wayback-content-error               |       57
     submitted     | spn2-error                          |       37
     submitted     | bad-redirect                        |       31
     submitted     | spn2-error:job-failed               |       14
     submitted     |                                     |       12
     submitted     | invalid-host-resolution             |       11
     submitted     | redirects-exceeded                  |        7
     submitted     | spn2-error:soft-time-limit-exceeded |        5
     submitted     | bad-gzip-encoding                   |        1
     submitted     | skip-url-blocklist                  |        1
                   | no-pdf-link                         |       42
                   | success                             |       25
                   | redirect-loop                       |       20
                   | terminal-bad-status                 |       11
                   | no-capture                          |        3
    (70 rows)
