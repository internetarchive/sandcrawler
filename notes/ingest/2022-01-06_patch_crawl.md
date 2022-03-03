
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

## More Seedlist (2022-02-08)

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
            AND ingest_file_result.updated >= '2022-01-12'
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
            AND ingest_file_result.terminal_url NOT LIKE '%www.archive.org%'
    -- ) TO '/srv/sandcrawler/tasks/patch_ingest_request_2022-02-08.rows.json';
    ) TO '/srv/sandcrawler/tasks/patch_terminal_url.2022-02-08.txt';
    => COPY 444764

    cat patch_terminal_url.2022-02-08.txt \
        | rg -v www.archive.org \
        | rg '://' \
        | rg -v '://10\.' \
        | rg -v '://172\.' \
        | rg -i '^http' \
        | sort -u -S 4G \
        | pv -l \
        > patch_terminal_url.2022-02-08.uniq.txt
    => 426k 0:00:04 [ 103k/s]

    cut -f3 -d/ patch_terminal_url.2022-02-08.uniq.txt | sort | uniq -c | sort -nr | head -n25
      60123 www.degruyter.com
      59314 arxiv.org
      43674 zenodo.org
      17771 doi.org
       9501 linkinghub.elsevier.com
       9379 www.mdpi.com
       5691 opendata.uni-halle.de
       5578 scholarlypublishingcollective.org
       5451 era.library.ualberta.ca
       4982 www.cairn.info
       4306 www.taylorfrancis.com
       4189 papers.ssrn.com
       4157 apps.crossref.org
       4089 www.sciencedirect.com
       4033 mdpi-res.com
       3763 dlc.mpg.de
       3408 osf.io
       2603 www.frontiersin.org
       2594 watermark.silverchair.com
       2569 journals.lww.com
       1787 underline.io
       1680 archiviostorico.fondazione1563.it
       1658 www.jstage.jst.go.jp
       1611 cyberleninka.ru
       1535 www.schoeningh.de

    cat patch_terminal_url.2022-02-08.txt | awk '{print "F+ " $1}' > patch_terminal_url.2022-02-08.schedule
    => Done

Copied to crawler svc206 and added to frontier.


## Bulk Ingest Requests (2022-02-28)

Note that we are skipping OAI-PMH here, because we just did a separate ingest
for those.

This is going to dump many duplicate lines (same `base_url`, multiple
requests), but that is fine. Expecting something like 7 million rows.

    COPY (
        -- SELECT ingest_file_result.terminal_url
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            (
                ingest_request.ingest_type = 'pdf'
                OR ingest_request.ingest_type = 'html'
            )
            AND ingest_file_result.updated <= '2022-02-08'
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
                -- ingest_request.link_source = 'oai'
                ingest_request.link_source = 'doi'
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
            AND ingest_file_result.terminal_url NOT LIKE '%www.archive.org%'
    ) TO '/srv/sandcrawler/tasks/patch_ingest_request_2022-02-28.rows.json';
    # COPY 3053219

    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/patch_ingest_request_2022-02-28.rows.json | pv -l | shuf > /srv/sandcrawler/tasks/patch_ingest_request_2022-02-28.ingest_request.json
    => DONE

    cat /srv/sandcrawler/tasks/patch_ingest_request_2022-02-28.ingest_request.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1
    => DONE

