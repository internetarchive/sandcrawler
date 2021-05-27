
New snapshot released 2021-02-18, finally getting around to a crawl two months
later.

Intend to do same style of crawl as in the past. One change is that
sandcrawler-db has moved to a focal VM.


## Transform and Load

    # in sandcrawler pipenv on sandcrawler1-vm (svc506)
    zcat /srv/sandcrawler/tasks/unpaywall_snapshot_2021-02-18T160139.jsonl.gz | ./scripts/unpaywall2ingestrequest.py - | pv -l > /srv/sandcrawler/tasks/unpaywall_snapshot_2021-02-18.ingest_request.json
    => 30.0M 3:14:59 [2.57k/s]

    cat /srv/sandcrawler/tasks/unpaywall_snapshot_2021-02-18.ingest_request.json | pv -l | ./persist_tool.py ingest-request -
    => Worker: Counter({'total': 30027007, 'insert-requests': 2703999, 'update-requests': 0})
    => JSON lines pushed: Counter({'total': 30027007, 'pushed': 30027007})

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
            -- AND date(ingest_request.created) > '2021-01-01'
            AND (ingest_file_result.status IS NULL
                OR ingest_file_result.status = 'no-capture')
    ) TO '/srv/sandcrawler/tasks/unpaywall_noingest_2021-02-18.rows.json';
    => COPY 3277484

    # previous, 2020-10 run: COPY 4216339

    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/unpaywall_noingest_2021-02-18.rows.json | pv -l | shuf > /srv/sandcrawler/tasks/unpaywall_noingest_2021-02-18.ingest_request.json
    => 3.28M 0:01:42 [32.1k/s]

Enqueue the whole batch:

    cat /srv/sandcrawler/tasks/unpaywall_noingest_2021-02-18.ingest_request.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1


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
     success                 | 26385866
     no-pdf-link             |  2132565
     no-capture              |  2092111
     redirect-loop           |  1732543
     terminal-bad-status     |  1504555
     wayback-content-error   |   357345
     wrong-mimetype          |   126070
     link-loop               |    76808
     cdx-error               |    22756
     null-body               |    22066
     wayback-error           |    13768
     gateway-timeout         |     3804
     petabox-error           |     3608
     spn2-cdx-lookup-failure |     1225
     redirects-exceeded      |      892
     invalid-host-resolution |      505
     bad-redirect            |      151
     spn2-error              |      108
     spn2-error:job-failed   |       91
     bad-gzip-encoding       |       27
    (20 rows)

Only the recent bulk ingest:

    SELECT ingest_file_result.status, COUNT(*)
    FROM ingest_request
    LEFT JOIN ingest_file_result
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE 
        ingest_request.ingest_type = 'pdf'
        AND ingest_request.link_source = 'unpaywall'
        AND date(ingest_request.created) > '2021-01-01'
    GROUP BY status
    ORDER BY COUNT DESC
    LIMIT 20;

             status          |  count  
    -------------------------+---------
     success                 | 1348623
     no-capture              | 1231582
     redirect-loop           |   45622
     no-pdf-link             |   37312
     terminal-bad-status     |   24162
     wrong-mimetype          |    6684
     link-loop               |    5757
     null-body               |    1288
     wayback-content-error   |    1123
     cdx-error               |     831
     petabox-error           |     697
     wayback-error           |     185
     invalid-host-resolution |      41
     gateway-timeout         |      29
     blocked-cookie          |      22
     bad-gzip-encoding       |      20
     spn2-cdx-lookup-failure |       7
     bad-redirect            |       4
     timeout                 |       3
     redirects-exceeded      |       3
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
                AND ingest_request.base_url NOT LIKE '%.archive.org%'
                AND ingest_request.base_url NOT LIKE '%://archive.org%'
                AND ingest_file_result.terminal_url NOT LIKE '%journals.sagepub.com%'
                AND ingest_file_result.terminal_url NOT LIKE '%pubs.acs.org%'
                AND ingest_file_result.terminal_url NOT LIKE '%ahajournals.org%'
                AND ingest_file_result.terminal_url NOT LIKE '%www.journal.csj.jp%'
                AND ingest_file_result.terminal_url NOT LIKE '%aip.scitation.org%'
                AND ingest_file_result.terminal_url NOT LIKE '%academic.oup.com%'
                AND ingest_file_result.terminal_url NOT LIKE '%tandfonline.com%'
                AND ingest_file_result.terminal_url NOT LIKE '%.archive.org%'
                AND ingest_file_result.terminal_url NOT LIKE '%://archive.org%'
        ) t1
    ) TO '/srv/sandcrawler/tasks/unpaywall_seedlist_2021-02-18.rows.json';
    => 2020-10: 2,936,404
    => 2021-04: 1,805,192

Prep ingest requests (for post-crawl use):

    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/unpaywall_seedlist_2021-02-18.rows.json | pv -l > /srv/sandcrawler/tasks/unpaywall_crawl_ingest_2021-02-18.json
    => 1.81M 0:01:27 [20.6k/s]

And actually dump seedlist(s):

    cat /srv/sandcrawler/tasks/unpaywall_seedlist_2021-02-18.rows.json | jq -r .base_url | sort -u -S 4G > /srv/sandcrawler/tasks/unpaywall_seedlist_2021-02-18.url.txt
    cat /srv/sandcrawler/tasks/unpaywall_seedlist_2021-02-18.rows.json | rg '"no-capture"' | jq -r .result.terminal_url | rg -v ^null$ | sort -u -S 4G > /srv/sandcrawler/tasks/unpaywall_seedlist_2021-02-18.terminal_url.txt
    cat /srv/sandcrawler/tasks/unpaywall_seedlist_2021-02-18.rows.json | rg -v '"no-capture"' | jq -r .base_url | sort -u -S 4G > /srv/sandcrawler/tasks/unpaywall_seedlist_2021-02-18.no_terminal_url.txt

    wc -l /srv/sandcrawler/tasks/unpaywall_seedlist_2021-02-18.*.txt
            6 /srv/sandcrawler/tasks/unpaywall_seedlist_2021-02-18.no_terminal_url.txt
      1668524 /srv/sandcrawler/tasks/unpaywall_seedlist_2021-02-18.terminal_url.txt
      1685717 /srv/sandcrawler/tasks/unpaywall_seedlist_2021-02-18.url.txt

## Post-Crawl Bulk Ingest

    cat /srv/sandcrawler/tasks/unpaywall_crawl_ingest_2021-02-18.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1
    => 1,804,211 consumer group lag

## Post-Ingest Stats

Overall status (unpaywall, all time):

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
     success                 | 27242251
     no-pdf-link             |  2746237
     redirect-loop           |  1821132
     terminal-bad-status     |  1553441
     no-capture              |   478559
     wayback-content-error   |   357390
     wrong-mimetype          |   127365
     link-loop               |    79389
     cdx-error               |    23170
     null-body               |    23169
     wayback-error           |    13704
     gateway-timeout         |     3803
     petabox-error           |     3642
     redirects-exceeded      |     1427
     spn2-cdx-lookup-failure |     1214
     invalid-host-resolution |      505
     bad-redirect            |      153
     spn2-error              |      107
     spn2-error:job-failed   |       91
     body-too-large          |       84
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
     accepted      | success                             |  1213335
     accepted      | no-pdf-link                         |    29292
     accepted      | redirect-loop                       |    12769
     accepted      | terminal-bad-status                 |    11264
     accepted      | no-capture                          |    10187
     accepted      | cdx-error                           |     1015
     accepted      | wayback-content-error               |      757
     accepted      | wrong-mimetype                      |      501
     accepted      | link-loop                           |      407
     accepted      | wayback-error                       |      207
     accepted      | petabox-error                       |      189
     accepted      | redirects-exceeded                  |      125
     accepted      | null-body                           |       34
     accepted      | spn2-cdx-lookup-failure             |        5
     accepted      | gateway-timeout                     |        4
     accepted      | blocked-cookie                      |        2
     accepted      | bad-redirect                        |        1
     accepted      | body-too-large                      |        1
     published     | success                             | 20196774
     published     | no-pdf-link                         |  2647969
     published     | redirect-loop                       |  1477558
     published     | terminal-bad-status                 |  1320013
     published     | wayback-content-error               |   351931
     published     | no-capture                          |   297603
     published     | wrong-mimetype                      |   115440
     published     | link-loop                           |    76431
     published     | cdx-error                           |    18125
     published     | null-body                           |    17559
     published     | wayback-error                       |    10466
     published     | petabox-error                       |     2684
     published     | gateway-timeout                     |     1979
     published     | redirects-exceeded                  |      947
     published     | spn2-cdx-lookup-failure             |      877
     published     | invalid-host-resolution             |      457
     published     | bad-redirect                        |      120
     published     | spn2-error:job-failed               |       77
     published     | spn2-error                          |       70
     published     | body-too-large                      |       39
     published     | bad-gzip-encoding                   |       24
     published     | timeout                             |       24
     published     | blocked-cookie                      |       23
     published     | spn2-error:soft-time-limit-exceeded |        4
     published     |                                     |        2
     published     | pending                             |        1
     published     | spn2-error:pending                  |        1
     published     | too-many-redirects                  |        1
     submitted     | success                             |  5832117
     submitted     | redirect-loop                       |   330785
     submitted     | terminal-bad-status                 |   222152
     submitted     | no-capture                          |   170766
     submitted     | no-pdf-link                         |    68934
     submitted     | wrong-mimetype                      |    11424
     submitted     | null-body                           |     5576
     submitted     | wayback-content-error               |     4702
     submitted     | cdx-error                           |     4030
     submitted     | wayback-error                       |     3031
     submitted     | link-loop                           |     2551
     submitted     | gateway-timeout                     |     1820
     submitted     | petabox-error                       |      769
     submitted     | redirects-exceeded                  |      355
     submitted     | spn2-cdx-lookup-failure             |      332
     submitted     | invalid-host-resolution             |       48
     submitted     | body-too-large                      |       44
     submitted     | spn2-error                          |       37
     submitted     | bad-redirect                        |       32
     submitted     | spn2-error:job-failed               |       14
     submitted     |                                     |       13
     submitted     | spn2-error:soft-time-limit-exceeded |        5
     submitted     | timeout                             |        4
     submitted     | bad-gzip-encoding                   |        3
     submitted     | skip-url-blocklist                  |        1
                   | no-pdf-link                         |       42
                   | success                             |       25
                   | redirect-loop                       |       20
                   | terminal-bad-status                 |       12
                   | no-capture                          |        3
    (76 rows)


Only the recent updates:

    SELECT ingest_file_result.status, COUNT(*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND date(ingest_request.created) > '2021-04-01'
        GROUP BY status
        ORDER BY COUNT DESC
        LIMIT 20;

             status          |  count
    -------------------------+---------
     success                 | 2192376
     no-capture              |  152183
     no-pdf-link             |  144174
     redirect-loop           |  125988
     terminal-bad-status     |   67307
     link-loop               |    8292
     wrong-mimetype          |    7942
     null-body               |    2270
     cdx-error               |    1223
     wayback-content-error   |    1147
     petabox-error           |     728
     wayback-error           |     155
     body-too-large          |      82
     invalid-host-resolution |      41
     gateway-timeout         |      28
     blocked-cookie          |      22
     bad-gzip-encoding       |      20
     timeout                 |       7
     bad-redirect            |       6
     redirects-exceeded      |       4
    (20 rows)

In total, this iteration of unpaywall ingest resulted in:

- 2,703,999 raw ingest requests (new URLs total)
- 1,231,582 (45.5%) of these had not been seen/crawled from any source yet
- 843,753 (31.2%) success from new heritrix crawling
- 2,192,376 (81.1%) total success (including crawled initially for other reasons; out of all new URLs including those not expected to be success)
