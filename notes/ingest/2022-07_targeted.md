
Heritrix follow-up crawl for recent bulk ingest of DOAJ, JALC, and DBLP URLs.

    export PATCHDATE=2022-07-29
    export CRAWLVM=wbgrp-svc279.us.archive.org
    export CRAWLNAME=TARGETED-ARTICLE-CRAWL-2022-07

## Seedlist Query

Terminal URLs dump:

    COPY (
        SELECT row_to_json(t) FROM (
            SELECT ingest_file_result.terminal_url, ingest_request.*
            FROM ingest_request
            LEFT JOIN ingest_file_result
                ON ingest_file_result.ingest_type = ingest_request.ingest_type
                AND ingest_file_result.base_url = ingest_request.base_url
            WHERE
                (
                    ingest_request.ingest_type = 'pdf'
                    OR ingest_request.ingest_type = 'html'
                )
                -- AND ingest_file_result.updated >= '2022-01-12'
                AND (
                    ingest_file_result.status = 'no-capture'
                    OR ingest_file_result.status = 'cdx-error'
                    OR ingest_file_result.status = 'wayback-error'
                    OR ingest_file_result.status = 'wayback-content-error'
                    OR ingest_file_result.status = 'petabox-error'
                    OR ingest_file_result.status LIKE 'spn2-%'
                    OR ingest_file_result.status = 'gateway-timeout'
                    OR (
                        ingest_file_result.status = 'terminal-bad-status'
                        AND (
                            ingest_file_result.terminal_status_code = 500
                            OR ingest_file_result.terminal_status_code = 502
                            OR ingest_file_result.terminal_status_code = 503
                            OR ingest_file_result.terminal_status_code = 429
                        )
                    )
                )
                AND (
                    ingest_request.link_source = 'doi'
                    OR ingest_request.link_source = 'doaj'
                    OR ingest_request.link_source = 'dblp'
                    OR ingest_request.link_source = 'arxiv'
                    OR ingest_request.link_source = 'pmc'
                    -- OR ingest_request.link_source = 'unpaywall'
                    -- OR ingest_request.link_source = 'oai'
                )

                AND ingest_file_result.terminal_url NOT LIKE '%mdz-nbn-resolving.de%'
                AND ingest_file_result.terminal_url NOT LIKE '%edoc.mpg.de%'
                AND ingest_file_result.terminal_url NOT LIKE '%orcid.org%'
                AND ingest_file_result.terminal_url NOT LIKE '%gateway.isiknowledge.com%'
                AND ingest_file_result.terminal_url NOT LIKE '%europmc.org%'
                AND ingest_file_result.terminal_url NOT LIKE '%arxiv.org%'
                -- AND ingest_file_result.terminal_url NOT LIKE 'https://doi.org/10.%'

                AND ingest_file_result.terminal_url NOT LIKE '%journals.sagepub.com%'
                AND ingest_file_result.terminal_url NOT LIKE '%pubs.acs.org%'
                AND ingest_file_result.terminal_url NOT LIKE '%ahajournals.org%'
                AND ingest_file_result.terminal_url NOT LIKE '%www.journal.csj.jp%'
                AND ingest_file_result.terminal_url NOT LIKE '%aip.scitation.org%'
                AND ingest_file_result.terminal_url NOT LIKE '%academic.oup.com%'
                AND ingest_file_result.terminal_url NOT LIKE '%tandfonline.com%'
                AND ingest_file_result.terminal_url NOT LIKE '%researchgate.net%'
                AND ingest_file_result.terminal_url NOT LIKE '%muse.jhu.edu%'
                AND ingest_file_result.terminal_url NOT LIKE '%omicsonline.org%'
                AND ingest_file_result.terminal_url NOT LIKE '%link.springer.com%'
                AND ingest_file_result.terminal_url NOT LIKE '%ieeexplore.ieee.org%'

                -- AND ingest_file_result.terminal_url NOT LIKE '%zenodo.org%'
                AND ingest_file_result.terminal_url NOT LIKE '%t2r2.star.titech.ac.jp%'
                AND ingest_file_result.terminal_url NOT LIKE '%www.google.com%'
                -- AND ingest_file_result.terminal_url NOT LIKE '%figshare.com%'
                -- AND ingest_file_result.terminal_url NOT LIKE '%springernature.figshare.com%'
                AND ingest_file_result.terminal_url NOT LIKE '%www.archive.org%'
        ) t
    ) TO '/srv/sandcrawler/tasks/patch_ingest_request_2022-07-29.rows.json';
    => COPY 3524573

    cat /srv/sandcrawler/tasks/patch_ingest_request_$PATCHDATE.rows.json \
        | rg -v "\\\\" \
        | jq -r .terminal_url \
        | rg '://' \
        | rg -i '^http' \
        | rg -v '://10\.' \
        | rg -v '://172\.' \
        | sort -u -S 4G \
        | pv -l \
        > /srv/sandcrawler/tasks/patch_terminal_url.$PATCHDATE.txt
    => 3.11M 0:01:08 [45.4k/s]

    # check top domains
    cut -f3 -d/ /srv/sandcrawler/tasks/patch_terminal_url.$PATCHDATE.txt | sort | uniq -c | sort -nr | head -n25
     624948 doi.org
     382492 www.jstage.jst.go.jp
     275087 www.mdpi.com
     157134 www.persee.fr
     108979 www.sciencedirect.com
      94375 www.scielo.br
      50834 onlinelibrary.wiley.com
      49991 journals.lww.com
      30354 www.frontiersin.org
      27963 doaj.org
      27058 www.e-periodica.ch
      24147 dl.acm.org
      23389 aclanthology.org
      22086 www.research-collection.ethz.ch
      21589 medien.die-bonn.de
      18866 www.ingentaconnect.com
      18583 doi.nrct.go.th
      18271 repositories.lib.utexas.edu
      17634 hdl.handle.net
      16366 archives.datapages.com
      15146 cgscholar.com
      13987 dl.gi.de
      13188 www.degruyter.com
      12503 ethos.bl.uk
      12304 preprints.jmir.org

    cat /srv/sandcrawler/tasks/patch_terminal_url.$PATCHDATE.txt | awk '{print "F+ " $1}' > /srv/sandcrawler/tasks/patch_terminal_url.$PATCHDATE.schedule
    => done

    scp /srv/sandcrawler/tasks/patch_terminal_url.$PATCHDATE.schedule $CRAWLVM:/tmp
    ssh $CRAWLVM sudo -u heritrix cp /tmp/patch_terminal_url.$PATCHDATE.schedule /0/ia-jobs/journal-crawls/$CRAWLNAME/action/


## Re-Ingest

Transform:

    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/patch_ingest_request_$PATCHDATE.rows.json | pv -l | shuf > /srv/sandcrawler/tasks/patch_ingest_request_$PATCHDATE.requests.json
    => 3.52M 0:01:37 [36.2k/s]

Ingest:

    cat /srv/sandcrawler/tasks/patch_ingest_request_$PATCHDATE.requests.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc350.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1
