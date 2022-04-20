
Want to do a crawl similar to recent "patch" crawls, where we run heritrix
crawls to "fill in" missing (`no-capture`) and failed dailing ingests (aka,
those requests coming from fatcat-changelog).

    export PATCHDATE=2022-04-20
    export CRAWLVM=wbgrp-svc279.us.archive.org
    export CRAWLNAME=TARGETED-ARTICLE-CRAWL-2022-04

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
                            ingest_file_result.terminal_status_code = 429
                            OR ingest_file_result.terminal_status_code = 500
                            OR ingest_file_result.terminal_status_code = 502
                            OR ingest_file_result.terminal_status_code = 503
                        )
                    )
                )
                AND (
                    ingest_request.link_source = 'doi'
                    OR ingest_request.link_source = 'arxiv'
                    OR ingest_request.link_source = 'doaj'
                    OR ingest_request.link_source = 'dblp'
                    OR ingest_request.link_source = 'pmc'
                    -- OR ingest_request.link_source = 'unpaywall'
                    -- OR ingest_request.link_source = 'oai'
                )

                AND ingest_file_result.terminal_url NOT LIKE '%mdz-nbn-resolving.de%'
                AND ingest_file_result.terminal_url NOT LIKE '%edoc.mpg.de%'
                AND ingest_file_result.terminal_url NOT LIKE '%doaj.org%'
                AND ingest_file_result.terminal_url NOT LIKE '%orcid.org%'
                AND ingest_file_result.terminal_url NOT LIKE '%gateway.isiknowledge.com%'
                -- AND ingest_file_result.terminal_url NOT LIKE '%europmc.org%'
                -- AND ingest_file_result.terminal_url NOT LIKE '%arxiv.org%'
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
    ) TO '/srv/sandcrawler/tasks/patch_ingest_request_2022-04-20.rows.json';
    # COPY 4842749

    cat /srv/sandcrawler/tasks/patch_ingest_request_$PATCHDATE.rows.json \
        | rg -v "\\\\" \
        | jq -r .terminal_url \
        | rg '://' \
        | rg -i '^http' \
        | rg -v www.archive.org \
        | rg -v '://10\.' \
        | rg -v '://172\.' \
        | sort -u -S 4G \
        | pv -l \
        > /srv/sandcrawler/tasks/patch_terminal_url.$PATCHDATE.txt
    # 4.75M 0:01:44 [45.4k/s]

    # check top domains
    cut -f3 -d/ /srv/sandcrawler/tasks/patch_terminal_url.$PATCHDATE.txt | sort | uniq -c | sort -nr | head -n25
    1515829 www.jstage.jst.go.jp
    1052953 doi.org
     241704 arxiv.org
     219543 www.sciencedirect.com
     178562 www.persee.fr
      84947 zenodo.org
      67397 www.mdpi.com
      65775 journals.lww.com
      58216 opg.optica.org
      50673 osf.io
      45776 www.degruyter.com
      36664 www.indianjournals.com
      35287 pubs.rsc.org
      33495 www.bmj.com
      33320 www.research-collection.ethz.ch
      29728 www.e-periodica.ch
      28338 iopscience.iop.org
      26364 www.cambridge.org
      23840 onlinelibrary.wiley.com
      23641 platform.almanhal.com
      22660 brill.com
      20288 www.osapublishing.org
      18561 cgscholar.com
      18539 doi.nrct.go.th
      15677 www.frontiersin.org

    cat /srv/sandcrawler/tasks/patch_terminal_url.$PATCHDATE.txt | awk '{print "F+ " $1}' > /srv/sandcrawler/tasks/patch_terminal_url.$PATCHDATE.schedule

    scp /srv/sandcrawler/tasks/patch_terminal_url.$PATCHDATE.schedule $CRAWLVM:/tmp
    ssh $CRAWLVM sudo -u heritrix cp /tmp/patch_terminal_url.$PATCHDATE.schedule /0/ia-jobs/journal-crawls/$CRAWLNAME/action/

TODO: starting with the "quarterly retry" script/query might make more sense?
TODO: are there any cases where we do a bulk ingest request, fail, and `terminal_url` is not set?

## Bulk Ingest Requests (post-crawl)

    cd /srv/sandcrawler/src/python
    sudo su sandcrawler
    pipenv run ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/patch_ingest_request_$PATCHDATE.rows.json | pv -l > /srv/sandcrawler/tasks/patch_ingest_request_$PATCHDATE.ingest_request.json

    cat /srv/sandcrawler/tasks/patch_ingest_request_$PATCHDATE.ingest_request.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1
