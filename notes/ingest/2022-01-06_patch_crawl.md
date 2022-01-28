
Starting another paper fulltext patch crawl, targetting recent OA content which
has failed to ingest, and platforms (arxiv, etc).

Specifically:

- "daily" changelog ingest requests from all time, which failed with various status codes
- pdf no-capture
- SPN errors
- terminal-bad-status with 5xx, 429
- gateway-timeout
- html no-capture
- html-resource-no-capture

Most of these are dumped in a single complex query (below), 

TODO: html-resource-no-capture (from error message? or do SPN requests separately?)


## Initial 'no-capture' Seedlist

Dump terminal URLs (will do ingest requests later, using similar command):

    COPY (  
        SELECT ingest_file_result.terminal_url
        -- SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            (
                ingest_request.ingest_type = 'pdf'
                OR ingest_request.ingest_type = 'html'
            )
            AND (
                ingest_file_result.status = 'no-capture'
                OR ingest_file_result.status = 'cdx-error'
                OR ingest_file_result.status = 'wayback-error'
                OR ingest_file_result.status = 'wayback-content-error'
                OR ingest_file_result.status = 'petabox-error'
                OR ingest_file_result.status = 'spn2-cdx-lookup-failure'
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
                ingest_request.link_source = 'oai'
                OR ingest_request.link_source = 'doi'
                OR ingest_request.link_source = 'arxiv'
                OR ingest_request.link_source = 'doaj'
                OR ingest_request.link_source = 'unpaywall'
                OR ingest_request.link_source = 'pmc'
            )

            AND ingest_request.link_source_id NOT LIKE 'oai:kb.dk:%'
            AND ingest_request.link_source_id NOT LIKE 'oai:bdr.oai.bsb-muenchen.de:%'
            AND ingest_request.link_source_id NOT LIKE 'oai:hispana.mcu.es:%'
            AND ingest_request.link_source_id NOT LIKE 'oai:bnf.fr:%'
            AND ingest_request.link_source_id NOT LIKE 'oai:ukm.si:%'
            AND ingest_request.link_source_id NOT LIKE 'oai:biodiversitylibrary.org:%'
            AND ingest_request.link_source_id NOT LIKE 'oai:hsp.org:%'
            AND ingest_request.link_source_id NOT LIKE 'oai:repec:%'
            AND ingest_request.link_source_id NOT LIKE 'oai:n/a:%'
            AND ingest_request.link_source_id NOT LIKE 'oai:quod.lib.umich.edu:%'
            AND ingest_request.link_source_id NOT LIKE 'oai:americanae.aecid.es:%'
            AND ingest_request.link_source_id NOT LIKE 'oai:www.irgrid.ac.cn:%'
            AND ingest_request.link_source_id NOT LIKE 'oai:espace.library.uq.edu:%'
            AND ingest_request.link_source_id NOT LIKE 'oai:edoc.mpg.de:%'
            AND ingest_request.link_source_id NOT LIKE 'oai:bibliotecadigital.jcyl.es:%'
            AND ingest_request.link_source_id NOT LIKE 'oai:repository.erciyes.edu.tr:%'
            AND ingest_request.link_source_id NOT LIKE 'oai:krm.or.kr:%'
            AND ingest_request.link_source_id NOT LIKE 'oai:hypotheses.org:%'

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
    -- ) TO '/srv/sandcrawler/tasks/patch_ingest_request_2022-01-12.rows.json';
    ) TO '/srv/sandcrawler/tasks/patch_terminal_url.2022-01-12.txt';
    => COPY 6389683

TODO: filter out archive.org/www.archive.org

    cat patch_terminal_url.2022-01-12.txt \
        | rg -v www.archive.org \
        | rg '://' \
        | rg -v '://10\.' \
        | rg -v '://172\.' \
        | rg -i '^http' \
        | sort -u -S 4G \
        | pv -l \
        > patch_terminal_url.2022-01-12.uniq.txt
    => 5.73M 0:00:47 [ 120k/s]

    # note: tweaks and re-ran the above after inspecting this output
    cut -f3 -d/ patch_terminal_url.2022-01-12.uniq.txt | sort | uniq -c | sort -nr | head -n25
     799045 doi.org
     317557 linkinghub.elsevier.com
     211091 arxiv.org
     204334 iopscience.iop.org
     139758 dialnet.unirioja.es
     130331 www.scielo.br
     124626 www.persee.fr
      85764 digitalrepository.unm.edu
      83913 www.mdpi.com
      79662 www.degruyter.com
      75703 www.e-periodica.ch
      72206 dx.doi.org
      69068 escholarship.org
      67848 idus.us.es
      57907 zenodo.org
      56624 ir.opt.ac.cn
      54983 projecteuclid.org
      52226 rep.bntu.by
      48376 osf.io
      48009 pubs.rsc.org
      46947 publikationen.ub.uni-frankfurt.de
      45564 www.research-collection.ethz.ch
      45153 dk.um.si
      43313 www.ssoar.info
      40543 scholarworks.umt.edu

TODO: cleanup ingest request table in sandcrawler-db:
- remove filtered OAI-PMH prefixes
- remove any invalid `base_url` (?)
