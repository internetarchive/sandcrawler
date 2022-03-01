
Going to run a combined crawl for `no-capture`, `no-pdf-link` and similar URL
statuses.

As a reminder, significant refactor of PDF URL extraction happened around
Oct/Nov 2020, so things not re-ingested since then should be retried.

1. first bulk re-process `no-pdf-link` statuses from OAI-PMH crawl past OA DOI past crawls
2. then heritrix crawl of old URLs from all sources (see status codes below)
3. bulk ingest specific sources and statuses (see below)

Status codes to crawl, with potentially split separate batches:

    no-capture
    IA errors
      cdx-error
      wayback-error
      wayback-content-error
      petabox-error
      spn2-cdx-lookup-failure
    gateway-timeout

Then, bulk ingest from these sources matching the above patterns, in this order:

- OA DOI (fatcat-ingest or fatcat-changelog source; will result in import)
- unpaywall (will result in import)
- OAI-PMH
- MAG

Current combined domain skip list (SQL filter syntax), for which we don't want
to bother retrying:

    '%journals.sagepub.com%'
    '%pubs.acs.org%'
    '%ahajournals.org%'
    '%www.journal.csj.jp%'
    '%aip.scitation.org%'
    '%academic.oup.com%'
    '%tandfonline.com%'
    '%://orcid.org/%'
    '%://doaj.org/%'
    '%://archive.org/%'
    '%://web.archive.org/%'
    '%://www.archive.org/%'

## DOI Ingest Status (2021-09-08)

Recently did some analysis of OAI-PMH overall status, so can re-do comparisons
there easily. What about overall DOI ingest? Would like counts so we can
compare before/after.

    SELECT ingest_file_result.status, COUNT(*)
    FROM ingest_request
    LEFT JOIN ingest_file_result
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE 
        ingest_request.ingest_type = 'pdf'
        AND ingest_request.link_source = 'doi'
        AND (
            ingest_request.ingest_request_source = 'fatcat-ingest'
            OR ingest_request.ingest_request_source = 'fatcat-changelog'
        )
    GROUP BY status
    ORDER BY COUNT DESC
    LIMIT 20;

                status             |  count
    -------------------------------+----------
     no-pdf-link                   | 10516478
     success                       |  5690862
     redirect-loop                 |  1827192
     no-capture                    |  1215179
     terminal-bad-status           |   650104
     link-loop                     |   610251
     blocked-cookie                |   353681
     gateway-timeout               |   341319
     too-many-redirects            |   307895
     forbidden                     |   306710
     spn2-cdx-lookup-failure       |   282955
     not-found                     |   273667
     cdx-error                     |   269082
     skip-url-blocklist            |   265689
     spn2-error                    |    87759
     wrong-mimetype                |    68993
     spn2-error:too-many-redirects |    58064
     wayback-error                 |    54152
     spn2-wayback-error            |    51752
     remote-server-error           |    45683
    (20 rows)

## `no-pdf-link` re-try bulk ingest

Specifically for past OAI-PMH and OA DOI crawls.

What are top terminal domains that would be retried? So that we can filter out
large ones we don't want to bother retrying.

    SELECT domain, COUNT(domain)
    FROM (
        SELECT
            substring(ingest_file_result.terminal_url FROM '[^/]+://([^/]*)') AS domain
        FROM ingest_request
        LEFT JOIN ingest_file_result 
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_file_result.status = 'no-pdf-link'
            AND (
                ingest_request.link_source = 'oai'
                OR (
                    ingest_request.link_source = 'doi'
                    AND (
                        ingest_request.ingest_request_source = 'fatcat-ingest'
                        OR ingest_request.ingest_request_source = 'fatcat-changelog'
                    )
                )
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
            AND ingest_file_result.terminal_url NOT LIKE '%europmc.org%'
            AND ingest_file_result.terminal_url NOT LIKE '%arxiv.org%'
            AND ingest_file_result.terminal_url NOT LIKE 'https://doi.org/10.%'
    ) t1
    WHERE t1.domain != ''
    GROUP BY domain
    ORDER BY COUNT DESC
    LIMIT 40;

                    domain                 | count  
    ---------------------------------------+--------
     ssl.fao.org                           | 862277
     www.e-periodica.ch                    | 828110
     zenodo.org                            | 686701
     plutof.ut.ee                          | 685440
     www.gbif.org                          | 669727
     dlc.library.columbia.edu              | 536018
     figshare.com                          | 383181
     juser.fz-juelich.de                   | 351519
     statisticaldatasets.data-planet.com   | 320415
     espace.library.uq.edu.au              | 310767
     invenio.nusl.cz                       | 309731
     doi.pangaea.de                        | 306311
     igi.indrastra.com                     | 297872
     bib-pubdb1.desy.de                    | 273565
     t2r2.star.titech.ac.jp                | 271907
     digi.ub.uni-heidelberg.de             | 265519
     www.sciencedirect.com                 | 263847
     publikationen.bibliothek.kit.edu      | 229960
     www.plate-archive.org                 | 209231
     www.degruyter.com                     | 189776
     spectradspace.lib.imperial.ac.uk:8443 | 187086
     hal.archives-ouvertes.fr              | 185513
     open.library.ubc.ca                   | 172821
     lup.lub.lu.se                         | 170063
     books.openedition.org                 | 169501
     orbi.uliege.be                        | 161443
     freidok.uni-freiburg.de               | 150310
     library.wur.nl                        | 124318
     digital.library.pitt.edu              | 116406
     www.research.manchester.ac.uk         | 115869
     www.bibliotecavirtualdeandalucia.es   | 114527
     repository.tue.nl                     | 112157
     www.google.com                        | 111569
     easy.dans.knaw.nl                     | 109608
     springernature.figshare.com           | 108597
     nbn-resolving.org                     | 107544
     scholarbank.nus.edu.sg                | 107299
     bibliotecavirtualdefensa.es           | 105501
     biblio.ugent.be                       | 100854
     ruj.uj.edu.pl                         |  99500
    (40 rows)

For a number of these domains, we do not expect any PDFs to be found, but are
going to re-ingest anyways so they get marked as 'blocked-*' in result table:

- ssl.fao.org
- plutof.ut.ee
- www.gbif.org

But some we are just going to skip anyways, because there *could* be PDFs, but
probably *aren't*:

- zenodo.org
- t2r2.star.titech.ac.jp
- www.google.com
- figshare.com
- springernature.figshare.com

Dump ingest requests:

    COPY (  
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_file_result.status = 'no-pdf-link'
            AND (
                ingest_request.link_source = 'oai'
                OR (
                    ingest_request.link_source = 'doi'
                    AND (
                        ingest_request.ingest_request_source = 'fatcat-ingest'
                        OR ingest_request.ingest_request_source = 'fatcat-changelog'
                    )
                )
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
            AND ingest_file_result.terminal_url NOT LIKE '%europmc.org%'
            AND ingest_file_result.terminal_url NOT LIKE '%arxiv.org%'
            AND ingest_file_result.terminal_url NOT LIKE 'https://doi.org/10.%'

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

            AND ingest_file_result.terminal_url NOT LIKE '%zenodo.org%'
            AND ingest_file_result.terminal_url NOT LIKE '%t2r2.star.titech.ac.jp%'
            AND ingest_file_result.terminal_url NOT LIKE '%www.google.com%'
            AND ingest_file_result.terminal_url NOT LIKE '%figshare.com%'
            AND ingest_file_result.terminal_url NOT LIKE '%springernature.figshare.com%'
    ) TO '/srv/sandcrawler/tasks/patch_ingest_request_2021-09-08.rows.json';
    => COPY 18040676

Transform and start ingest:

    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/patch_ingest_request_2021-09-08.rows.json | pv -l | shuf > /srv/sandcrawler/tasks/patch_ingest_request_2021-09-08.ingest_request.json
    => 18.0M 0:06:45 [44.5k/s]

    cat /srv/sandcrawler/tasks/patch_ingest_request_2021-09-08.ingest_request.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests -p -1
    => DONE

## Progress Check

OAI-PMH query:

    SELECT ingest_file_result.status, COUNT(*)
    FROM ingest_request
    LEFT JOIN ingest_file_result
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE 
        ingest_request.ingest_type = 'pdf'
        AND ingest_request.link_source = 'oai'
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
        AND ingest_request.base_url NOT LIKE '%www.kb.dk%'
        AND ingest_request.base_url NOT LIKE '%kb-images.kb.dk%'
        AND ingest_request.base_url NOT LIKE '%mdz-nbn-resolving.de%'
        AND ingest_request.base_url NOT LIKE '%aggr.ukm.um.si%'
        AND ingest_request.base_url NOT LIKE '%edoc.mpg.de%'
        AND ingest_request.base_url NOT LIKE '%doaj.org%'
        AND ingest_request.base_url NOT LIKE '%orcid.org%'
        AND ingest_request.base_url NOT LIKE '%gateway.isiknowledge.com%'
        AND ingest_request.link_source_id NOT LIKE 'oai:hypotheses.org:%'
    GROUP BY status
    ORDER BY COUNT DESC
    LIMIT 20;

             status          |  count   
    -------------------------+----------
     success                 | 13258356
     no-pdf-link             |  8685519
     no-capture              |  4765663
     redirect-loop           |  1557731
     terminal-bad-status     |   803373
     link-loop               |   453999
     wrong-mimetype          |   440230
     null-body               |    71457
     cdx-error               |    18426
                             |    15275
     petabox-error           |    13408
     wayback-error           |    11845
     blocked-cookie          |    11580
     skip-url-blocklist      |     7761
     wayback-content-error   |      383
     spn2-cdx-lookup-failure |      362
     gateway-timeout         |      320
     body-too-large          |      207
     spn2-error:job-failed   |      191
     redirects-exceeded      |      120
    (20 rows)

OAI-PMH compared to a couple weeks ago:

    13258356-12872279 = +386,077 success
    8685519-9329602 =   -644,083 no-pdf-link
    4765663-4696362 =    +69,301 no-capture
    803373-660418 =     +142,955 terminal-bad-status

OA DOI ingest:

    SELECT ingest_file_result.status, COUNT(*)
    FROM ingest_request
    LEFT JOIN ingest_file_result
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE 
        ingest_request.ingest_type = 'pdf'
        AND ingest_request.link_source = 'doi'
        AND (
            ingest_request.ingest_request_source = 'fatcat-ingest'
            OR ingest_request.ingest_request_source = 'fatcat-changelog'
        )
    GROUP BY status
    ORDER BY COUNT DESC
    LIMIT 20;


                status             |  count  
    -------------------------------+---------
     no-pdf-link                   | 6693547
     success                       | 5979016
     skip-url-blocklist            | 3080986
     no-capture                    | 1876914
     redirect-loop                 | 1872817
     terminal-bad-status           |  656674
     link-loop                     |  624290
     blocked-cookie                |  448001
     gateway-timeout               |  351896
     too-many-redirects            |  307895
     forbidden                     |  306710
     spn2-cdx-lookup-failure       |  301312
     cdx-error                     |  279766
     not-found                     |  273667
     wrong-mimetype                |   83289
     spn2-error                    |   76806
     spn2-error:too-many-redirects |   58064
     wayback-error                 |   54278
     spn2-wayback-error            |   51768
     remote-server-error           |   45683
    (20 rows)

OA DOI changes:

    5979016-5690862 =    +288,154   success
    6693547-10516478 = -3,822,931   no-pdf-link (still many!)
    1876914-1215179 =    +661,735   no-capture
    3080986-265689 =   +2,815,297   skip-url-blocklist

Overall about half a million new 'success', pretty good. over 750k new
no-capture for crawling.

## Seedlist Dumps

Note that this is just seedlists, not full ingest requests.

    COPY (  
        SELECT ingest_file_result.terminal_url
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND (
                ingest_file_result.status = 'no-capture'
                OR ingest_file_result.status = 'cdx-error'
                OR ingest_file_result.status = 'wayback-error'
                OR ingest_file_result.status = 'wayback-content-error'
                OR ingest_file_result.status = 'petabox-error'
                OR ingest_file_result.status = 'spn2-cdx-lookup-failure'
                OR ingest_file_result.status = 'gateway-timeout'
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
            AND ingest_file_result.terminal_url NOT LIKE '%europmc.org%'
            AND ingest_file_result.terminal_url NOT LIKE '%arxiv.org%'

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

    ) TO '/srv/sandcrawler/tasks/patch_2021-09-16_terminal_seedlist.txt';
    => 6,354,365

Then run the actual patch crawl!

## Ingest Requests for Bulk Retry (2022-01-06)

Crawl has just about completed, so running another round of bulk ingest
requests, slightly updated to allow `https://doi.org/10*` in terminal URL:

    COPY (  
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_file_result.updated <= '2022-01-01'
            AND (
                ingest_file_result.status = 'no-capture'
                OR ingest_file_result.status = 'cdx-error'
                OR ingest_file_result.status = 'wayback-error'
                OR ingest_file_result.status = 'wayback-content-error'
                OR ingest_file_result.status = 'petabox-error'
                OR ingest_file_result.status = 'spn2-cdx-lookup-failure'
                OR ingest_file_result.status = 'gateway-timeout'
            )
            AND (
                ingest_request.link_source = 'oai'
                OR (
                    ingest_request.link_source = 'doi'
                    AND (
                        ingest_request.ingest_request_source = 'fatcat-ingest'
                        OR ingest_request.ingest_request_source = 'fatcat-changelog'
                    )
                )
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

            AND ingest_file_result.terminal_url NOT LIKE '%zenodo.org%'
            AND ingest_file_result.terminal_url NOT LIKE '%t2r2.star.titech.ac.jp%'
            AND ingest_file_result.terminal_url NOT LIKE '%www.google.com%'
            AND ingest_file_result.terminal_url NOT LIKE '%figshare.com%'
            AND ingest_file_result.terminal_url NOT LIKE '%springernature.figshare.com%'
    ) TO '/srv/sandcrawler/tasks/patch_ingest_request_2022-01-06.rows.json';
    => 4,488,193

    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/patch_ingest_request_2022-01-06.rows.json | pv -l | shuf > /srv/sandcrawler/tasks/patch_ingest_request_2022-01-06.ingest_request.json
    => DONE

    cat /srv/sandcrawler/tasks/patch_ingest_request_2022-01-06.ingest_request.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1
    => TIMEDOUT
    => (probably due to re-assignment)
    => DONE

## Stats Again (just OAI-PMH)

OAI-PMH query:

    SELECT ingest_file_result.status, COUNT(*)
    FROM ingest_request
    LEFT JOIN ingest_file_result
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE 
        ingest_request.ingest_type = 'pdf'
        AND ingest_request.link_source = 'oai'
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
        AND ingest_request.base_url NOT LIKE '%www.kb.dk%'
        AND ingest_request.base_url NOT LIKE '%kb-images.kb.dk%'
        AND ingest_request.base_url NOT LIKE '%mdz-nbn-resolving.de%'
        AND ingest_request.base_url NOT LIKE '%aggr.ukm.um.si%'
        AND ingest_request.base_url NOT LIKE '%edoc.mpg.de%'
        AND ingest_request.base_url NOT LIKE '%doaj.org%'
        AND ingest_request.base_url NOT LIKE '%orcid.org%'
        AND ingest_request.base_url NOT LIKE '%gateway.isiknowledge.com%'
        AND ingest_request.link_source_id NOT LIKE 'oai:hypotheses.org:%'
    GROUP BY status
    ORDER BY COUNT DESC
    LIMIT 20;

On 2022-02-08:

            status         |  count
    -----------------------+----------
     success               | 13505143
     no-pdf-link           |  8741007
     no-capture            |  4429986
     redirect-loop         |  1566611
     terminal-bad-status   |   816162
     link-loop             |   459006
     wrong-mimetype        |   448983
     null-body             |    71871
     cdx-error             |    19055
                           |    15275
     petabox-error         |    11713
     blocked-cookie        |    11664
     wayback-error         |     8745
     skip-url-blocklist    |     7828
     max-hops-exceeded     |     2031
     wayback-content-error |      338
     body-too-large        |      280
     spn2-error:job-failed |      191
     bad-redirect          |      134
     redirects-exceeded    |      120
    (20 rows)


On 2022-02-28, after bulk ingest completed:

            status         |  count   
    -----------------------+----------
     success               | 14668123
     no-pdf-link           |  8822460
     no-capture            |  2987565
     redirect-loop         |  1629015
     terminal-bad-status   |   917851
     wrong-mimetype        |   466512
     link-loop             |   460941
     null-body             |    71457
     cdx-error             |    19636
     petabox-error         |    16198
                           |    15275
     blocked-cookie        |    11885
     wayback-error         |     8779
     skip-url-blocklist    |     7838
     empty-blob            |     5906
     max-hops-exceeded     |     5563
     wayback-content-error |      355
     body-too-large        |      329
     spn2-error:job-failed |      191
     bad-redirect          |      137
    (20 rows)


Comparing to a couple months ago:

    14668123-13258356 = +1,409,767  success
    8822460-8685519 =   +  136,941  no-pdf-link
    2987565-4765663 =   -1,778,098  no-capture
    917851-803373 =     +  114,478  terminal-bad-status

