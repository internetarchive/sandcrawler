
New snapshot released 2021-07-02. Should be "boring" ingest and crawl.


## Transform and Load

    # in sandcrawler pipenv on sandcrawler1-vm (svc506)
    zcat /srv/sandcrawler/tasks/unpaywall_snapshot_2021-07-02T151134.jsonl.gz | ./scripts/unpaywall2ingestrequest.py - | pv -l > /srv/sandcrawler/tasks/unpaywall_snapshot_2021-07-02.ingest_request.json
    => 32.2M 3:01:52 [2.95k/s]

    cat /srv/sandcrawler/tasks/unpaywall_snapshot_2021-07-02.ingest_request.json | pv -l | ./persist_tool.py ingest-request -
    => Worker: Counter({'total': 32196260, 'insert-requests': 3325954, 'update-requests': 0})
    => JSON lines pushed: Counter({'total': 32196260, 'pushed': 32196260})


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
    ) TO '/srv/sandcrawler/tasks/unpaywall_noingest_2021-07-02.rows.json';
    => COPY 3556146

    # previous, 2020-10 run: COPY 4216339
    # previous, 2021-07 run: COPY 3277484

Oops, should have run instead, with the date filter:

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND date(ingest_request.created) > '2021-07-01'
            AND (ingest_file_result.status IS NULL
                OR ingest_file_result.status = 'no-capture')
    ) TO '/srv/sandcrawler/tasks/unpaywall_noingest_2021-07-02.rows.json';

But didn't, so processed all instead.

    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/unpaywall_noingest_2021-07-02.rows.json | pv -l | shuf > /srv/sandcrawler/tasks/unpaywall_noingest_2021-07-02.ingest_request.json
    => 3.56M 0:01:59 [29.8k/s]

Enqueue the whole batch:

    cat /srv/sandcrawler/tasks/unpaywall_noingest_2021-07-02.ingest_request.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1
    => done, on 2021-07-13


## Check Pre-Crawl Status

Only the recent bulk ingest:

    SELECT ingest_file_result.status, COUNT(*)
    FROM ingest_request
    LEFT JOIN ingest_file_result
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE 
        ingest_request.ingest_type = 'pdf'
        AND ingest_request.link_source = 'unpaywall'
        AND date(ingest_request.created) > '2021-07-01'
    GROUP BY status
    ORDER BY COUNT DESC
    LIMIT 20;

             status          |  count
    -------------------------+---------
     no-capture              | 1831827
     success                 | 1343604
     redirect-loop           |  103999
     terminal-bad-status     |   19845
     no-pdf-link             |   17448
     link-loop               |    5027
     wrong-mimetype          |    2270
     cdx-error               |     523
     body-too-large          |     321
     null-body               |     298
     wayback-content-error   |     242
     petabox-error           |     155
     gateway-timeout         |     138
     invalid-host-resolution |     120
     wayback-error           |     109
     blocked-cookie          |       9
     timeout                 |       7
                             |       3
     bad-redirect            |       3
     spn2-cdx-lookup-failure |       3
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
                AND date(ingest_request.created) > '2021-07-01'
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
    ) TO '/srv/sandcrawler/tasks/unpaywall_seedlist_2021-07-02.rows.json';
    => COPY 1743186

Prep ingest requests (for post-crawl use):

    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/unpaywall_seedlist_2021-07-02.rows.json | pv -l > /srv/sandcrawler/tasks/unpaywall_crawl_ingest_2021-07-02.json
    => 1.74M 0:01:33 [18.6k/s]

And actually dump seedlist(s):

    cat /srv/sandcrawler/tasks/unpaywall_seedlist_2021-07-02.rows.json | jq -r .base_url | sort -u -S 4G > /srv/sandcrawler/tasks/unpaywall_seedlist_2021-07-02.url.txt
    cat /srv/sandcrawler/tasks/unpaywall_seedlist_2021-07-02.rows.json | rg '"no-capture"' | jq -r .result.terminal_url | rg -v ^null$ | sort -u -S 4G > /srv/sandcrawler/tasks/unpaywall_seedlist_2021-07-02.terminal_url.txt
    cat /srv/sandcrawler/tasks/unpaywall_seedlist_2021-07-02.rows.json | rg -v '"no-capture"' | jq -r .base_url | sort -u -S 4G > /srv/sandcrawler/tasks/unpaywall_seedlist_2021-07-02.no_terminal_url.txt

    wc -l /srv/sandcrawler/tasks/unpaywall_seedlist_2021-07-02.*.txt
            1 /srv/sandcrawler/tasks/unpaywall_seedlist_2021-07-02.no_terminal_url.txt
      1643963 /srv/sandcrawler/tasks/unpaywall_seedlist_2021-07-02.terminal_url.txt
      1644028 /srv/sandcrawler/tasks/unpaywall_seedlist_2021-07-02.url.txt
      3287992 total

Then run crawl (see `journal-crawls` git repo).

## Post-Crawl Bulk Ingest

    cat /srv/sandcrawler/tasks/unpaywall_crawl_ingest_2021-07-02.json | rg -v "\\\\" | jq . -c | pv -l | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1
    => 1.74M 0:01:59 [14.6k/s]

## Post-Ingest Stats

Only the recent updates:

    SELECT ingest_file_result.status, COUNT(*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND date(ingest_request.created) > '2021-07-01'
        GROUP BY status
        ORDER BY COUNT DESC
        LIMIT 20;

             status          |  count  
    -------------------------+---------
     success                 | 2690258
     redirect-loop           |  227328
     no-capture              |  157368
     terminal-bad-status     |  118943
     no-pdf-link             |   92698
     blocked-cookie          |   19478
     link-loop               |    9249
     wrong-mimetype          |    4918
     cdx-error               |    1786
     wayback-error           |    1497
     null-body               |    1302
     body-too-large          |     433
     wayback-content-error   |     245
     petabox-error           |     171
     gateway-timeout         |     138
     invalid-host-resolution |     120
     timeout                 |      12
     bad-redirect            |       4
                             |       3
     spn2-cdx-lookup-failure |       1
    (20 rows)

Only the recent updates, by publication stage:

    SELECT ingest_request.release_stage, ingest_file_result.status, COUNT(*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND date(ingest_request.created) > '2021-07-01'
        GROUP BY release_stage, status
        ORDER BY release_stage, COUNT DESC
        LIMIT 100;

     release_stage |         status          |  count  
    ---------------+-------------------------+---------
     accepted      | success                 |  103144
     accepted      | no-pdf-link             |   53981
     accepted      | terminal-bad-status     |    4102
     accepted      | link-loop               |    2799
     accepted      | no-capture              |    2315
     accepted      | redirect-loop           |    2171
     accepted      | blocked-cookie          |     234
     accepted      | cdx-error               |     140
     accepted      | wayback-error           |     101
     accepted      | wrong-mimetype          |      38
     accepted      | null-body               |      10
     accepted      | petabox-error           |       5
     accepted      | wayback-content-error   |       4
     accepted      | gateway-timeout         |       2
     accepted      | body-too-large          |       2
     published     | success                 | 1919100
     published     | no-capture              |  130104
     published     | redirect-loop           |  127482
     published     | terminal-bad-status     |   43118
     published     | no-pdf-link             |   33505
     published     | blocked-cookie          |   19034
     published     | link-loop               |    6241
     published     | wrong-mimetype          |    4163
     published     | null-body               |    1195
     published     | cdx-error               |    1151
     published     | wayback-error           |    1105
     published     | wayback-content-error   |     197
     published     | body-too-large          |     195
     published     | petabox-error           |     118
     published     | gateway-timeout         |      35
     published     | invalid-host-resolution |      13
     published     | timeout                 |       8
     published     | bad-redirect            |       2
     published     | spn2-cdx-lookup-failure |       1
     published     | bad-gzip-encoding       |       1
     submitted     | success                 |  668014
     submitted     | redirect-loop           |   97675
     submitted     | terminal-bad-status     |   71723
     submitted     | no-capture              |   24949
     submitted     | no-pdf-link             |    5212
     submitted     | wrong-mimetype          |     717
     submitted     | cdx-error               |     495
     submitted     | wayback-error           |     291
     submitted     | body-too-large          |     236
     submitted     | blocked-cookie          |     210
     submitted     | link-loop               |     209
     submitted     | invalid-host-resolution |     107
     submitted     | gateway-timeout         |     101
     submitted     | null-body               |      97
     submitted     | petabox-error           |      48
     submitted     | wayback-content-error   |      44
     submitted     | timeout                 |       4
     submitted     |                         |       3
     submitted     | bad-redirect            |       2
     submitted     | remote-server-error     |       1
    (55 rows)

In total, this iteration of unpaywall ingest resulted in:

- 3,325,954 raw ingest requests (new URLs total)
- 1,743,186 (52% of all) of these had not been seen/crawled from any source yet (?), and attempted to crawl
- 1,346,654 (77% of crawled) success from new heritrix crawling
- 2,690,258 (80%) total success (including crawled initially for other reasons; out of all new URLs including those not expected to be success)

## Live Ingest Follow-Up

Will run SPN requests on the ~160k `no-capture` URLs:

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND date(ingest_request.created) > '2021-07-01'
            AND (ingest_file_result.status IS NULL
                OR ingest_file_result.status = 'no-capture')
    ) TO '/srv/sandcrawler/tasks/unpaywall_noingest_2021-07-30.rows.json';
    => COPY 157371

    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/unpaywall_noingest_2021-07-30.rows.json | pv -l | shuf > /srv/sandcrawler/tasks/unpaywall_noingest_2021-07-30.ingest_request.json
    => 157k 0:00:04 [31.6k/s]

Enqueue the whole batch:

    cat /srv/sandcrawler/tasks/unpaywall_noingest_2021-07-30.ingest_request.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests -p -1
    => DONE
