
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
