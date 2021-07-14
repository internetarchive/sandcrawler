
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

In total, this iteration of unpaywall ingest resulted in:

- XXX raw ingest requests (new URLs total)
- XXX (YY%) of these had not been seen/crawled from any source yet
- XXX (YY%) success from new heritrix crawling
- XXX (YY%) total success (including crawled initially for other reasons; out of all new URLs including those not expected to be success)
