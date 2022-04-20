
New unpaywall snapshot from `2022-03-09`.

This will probably be the last unpaywall crawl? Will switch to openalex in the
future, because we can automate that ingest process, and run it on our own
schedule.

## Download and Archive

    wget 'https://unpaywall-data-snapshots.s3.us-west-2.amazonaws.com/unpaywall_snapshot_2022-03-09T083001.jsonl.gz'
    # 2022-04-09 22:31:43 (98.9 KB/s) - ‘unpaywall_snapshot_2022-03-09T083001.jsonl.gz’ saved [29470830470/29470830470]

    export SNAPSHOT=2022-03-09
    ia upload unpaywall_snapshot_$SNAPSHOT unpaywall_snapshot_$SNAPSHOT*.jsonl.gz -m title:"Unpaywall Metadata Snapshot ($SNAPSHOT)" -m collection:ia_biblio_metadata -m creator:creator -m date:$SNAPSHOT

    # if needed
    scp unpaywall_snapshot_$SNAPSHOT*.jsonl.gz wbgrp-svc506.us.archive.org:/srv/sandcrawler/tasks

## Transform and Load

    # in sandcrawler pipenv on sandcrawler1-vm (svc506)
    cd /srv/sandcrawler/src/python
    sudo su sandcrawler
    pipenv shell

    zcat /srv/sandcrawler/tasks/unpaywall_snapshot_$SNAPSHOT*.jsonl.gz | ./scripts/unpaywall2ingestrequest.py - | pv -l > /srv/sandcrawler/tasks/unpaywall_snapshot_$SNAPSHOT.ingest_request.json
    # 34.9M 3:02:32 [3.19k/s]

    cat /srv/sandcrawler/tasks/unpaywall_snapshot_$SNAPSHOT.ingest_request.json | pv -l | ./persist_tool.py ingest-request -
    # 34.9M 5:23:15 [1.80k/s]
    # Worker: Counter({'total': 34908779, 'insert-requests': 6129630, 'update-requests': 0})
    # JSON lines pushed: Counter({'total': 34908779, 'pushed': 34908779})

So about 6.1M new ingest request rows.

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
            -- take "all time" instead of just this recent capture
            -- AND date(ingest_request.created) > '2021-01-01'
            AND (ingest_file_result.status IS NULL
                OR ingest_file_result.status = 'no-capture')
    ) TO '/srv/sandcrawler/tasks/unpaywall_noingest_2022-03-09.rows.json';
    => COPY 6025671

    # transform
    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/unpaywall_noingest_$SNAPSHOT.rows.json | pv -l | shuf > /srv/sandcrawler/tasks/unpaywall_noingest_$SNAPSHOT.ingest_request.json
    # 6.03M 0:03:26 [29.1k/s]

    # enqueue for bulk processing
    cat /srv/sandcrawler/tasks/unpaywall_noingest_$SNAPSHOT.ingest_request.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1


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
        AND date(ingest_request.created) > '2022-04-01'
    GROUP BY status
    ORDER BY COUNT DESC
    LIMIT 20;


## Dump Seedlist

Dump rows for crawling:

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
                -- AND date(ingest_request.created) > '2022-04-01'
                AND ingest_request.link_source = 'unpaywall'
                AND (ingest_file_result.status = 'no-capture'
                    OR ingest_file_result.status = 'cdx-error'
                    OR ingest_file_result.status = 'wayback-error'
                    OR ingest_file_result.status = 'gateway-timeout'
                    OR ingest_file_result.status LIKE 'spn2-%'
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
    ) TO '/srv/sandcrawler/tasks/unpaywall_seedlist_2022-03-09.rows.json';

Prep ingest requests (for post-crawl use):

    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.rows.json | pv -l > /srv/sandcrawler/tasks/unpaywall_crawl_ingest_$SNAPSHOT.json

And actually dump seedlist(s):

    cat /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.rows.json | jq -r .base_url | sort -u -S 4G > /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.url.txt
    cat /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.rows.json | rg '"no-capture"' | jq -r .result.terminal_url | rg -v ^null$ | sort -u -S 4G > /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.terminal_url.txt
    cat /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.rows.json | rg -v '"no-capture"' | jq -r .base_url | sort -u -S 4G > /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.no_terminal_url.txt

    wc -l /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.*.txt

Then run crawl (see `journal-crawls` git repo), including frontier generation.
