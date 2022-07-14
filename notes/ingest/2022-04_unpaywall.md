
New unpaywall snapshot from `2022-03-09`.

This will probably be the last unpaywall crawl? Will switch to openalex in the
future, because we can automate that ingest process, and run it on our own
schedule.

    export SNAPSHOT=2022-03-09
    export CRAWLVM=wbgrp-svc279.us.archive.org
    export CRAWLNAME=UNPAYWALL-CRAWL-2022-04

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

             status          |  count
    -------------------------+---------
     no-capture              | 3330232
     success                 | 2455102
     redirect-loop           |  197117
     terminal-bad-status     |   82618
     no-pdf-link             |   33046
     blocked-cookie          |   16078
     link-loop               |    6745
     wrong-mimetype          |    3416
     wayback-error           |    1385
     empty-blob              |    1142
     cdx-error               |     820
     body-too-large          |     292
     bad-gzip-encoding       |     281
     wayback-content-error   |     267
                             |     253
     petabox-error           |     215
     skip-url-blocklist      |     185
     null-body               |     179
     spn2-cdx-lookup-failure |      89
     gateway-timeout         |      73
    (20 rows)

After prior "TARGETED" crawl and bulk ingest finished:

             status          |  count
    -------------------------+---------
     no-capture              | 3330055
     success                 | 2455279
     redirect-loop           |  197117
     terminal-bad-status     |   82618
     no-pdf-link             |   33046
     blocked-cookie          |   16079
     link-loop               |    6745
     wrong-mimetype          |    3416
     wayback-error           |    1385
     empty-blob              |    1142
     cdx-error               |     820
     body-too-large          |     292
     bad-gzip-encoding       |     281
     wayback-content-error   |     267
                             |     253
     petabox-error           |     215
     skip-url-blocklist      |     185
     null-body               |     179
     spn2-cdx-lookup-failure |      89
     gateway-timeout         |      73
    (20 rows)

Almost no change, which makes sense because of the `ingest_request.created`
filter.


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
                AND ingest_request.base_url NOT LIKE '%://doi.org/10.48550/%'
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
    => before ingest and arxiv.org DOI exclusion: COPY 3309091
    => COPY 3308914


Prep ingest requests (for post-crawl use):

    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.rows.json | pv -l > /srv/sandcrawler/tasks/unpaywall_crawl_ingest_$SNAPSHOT.json
    => 3.31M 0:02:22 [23.2k/s]

And actually dump seedlist(s):

    cat /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.rows.json | jq -r .base_url | sort -u -S 4G > /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.url.txt
    cat /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.rows.json | rg '"no-capture"' | jq -r .result.terminal_url | rg -v ^null$ | sort -u -S 4G > /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.terminal_url.txt
    cat /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.rows.json | rg -v '"no-capture"' | jq -r .base_url | sort -u -S 4G > /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.no_terminal_url.txt

    cat /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.no_terminal_url.txt /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.terminal_url.txt | awk '{print "F+ " $1}' | shuf > /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.schedule

    wc -l /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT*
            15 /srv/sandcrawler/tasks/unpaywall_seedlist_2022-03-09.no_terminal_url.txt
       3308914 /srv/sandcrawler/tasks/unpaywall_seedlist_2022-03-09.rows.json
       3028879 /srv/sandcrawler/tasks/unpaywall_seedlist_2022-03-09.terminal_url.txt
       3038725 /srv/sandcrawler/tasks/unpaywall_seedlist_2022-03-09.url.txt

Inject seedlist into crawler:

    scp /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.schedule $CRAWLVM:/tmp
    ssh $CRAWLVM sudo -u heritrix cp /tmp/unpaywall_seedlist_$SNAPSHOT.schedule /0/ia-jobs/journal-crawls/$CRAWLNAME/action/

Top domains?

    cat /srv/sandcrawler/tasks/unpaywall_seedlist_$SNAPSHOT.schedule | cut -f2 -d' ' | cut -f3 -d/ | sort -S 4G | uniq -c |  sort -nr | head -n20
     158497 www.scielo.br
     144732 onlinelibrary.wiley.com
     129349 www.researchsquare.com
      94923 hal.archives-ouvertes.fr
      69293 openresearchlibrary.org
      64584 www.cell.com
      60033 link.springer.com
      50528 www.degruyter.com
      49737 projecteuclid.org
      45841 www.jstage.jst.go.jp
      44819 www.mdpi.com
      44325 ieeexplore.ieee.org
      38091 dr.lib.iastate.edu
      31030 www.nature.com
      30300 discovery.ucl.ac.uk
      27692 ntrs.nasa.gov
      24215 orca.cardiff.ac.uk
      23653 www.frontiersin.org
      23474 pure.rug.nl
      22660 www.sciencedirect.com


## Post-Crawl bulk ingest

    # enqueue for bulk processing
    cat /srv/sandcrawler/tasks/unpaywall_crawl_ingest_$SNAPSHOT.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc350.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1
    # done: 2022-07-06

## Post-Crawl, Post-Ingest Stats

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

             status          |  count  
    -------------------------+---------
     success                 | 4784948 => +2,329,669  ~77%
     redirect-loop           |  485270 => +  288,153  ~10%
     no-capture              |  317598 => -3,012,457
     terminal-bad-status     |  267853 => +  185,235  ~ 6%
     no-pdf-link             |  118303 => +   85,257
     blocked-cookie          |  111373 => +   95,294
     skip-url-blocklist      |   19368
     link-loop               |    9091
     wrong-mimetype          |    7163
     cdx-error               |    2516
     empty-blob              |    1961
     wayback-error           |    1922
     body-too-large          |     509
     petabox-error           |     416
     wayback-content-error   |     341
     bad-gzip-encoding       |     281
                             |     253
     null-body               |     179
     spn2-cdx-lookup-failure |      89
     gateway-timeout         |      73
    (20 rows)

Groovy!
