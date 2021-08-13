
Just a "patch" of previous OAI-PMH crawl/ingest: re-ingesting and potentially
re-crawling content which failed to ingest the first time.

## Basic Counts

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
        AND ingest_request.base_url NOT LIKE '%www.kb.dk%'
        AND ingest_request.base_url NOT LIKE '%kb-images.kb.dk%'
        AND ingest_request.base_url NOT LIKE '%mdz-nbn-resolving.de%'
        AND ingest_request.base_url NOT LIKE '%aggr.ukm.um.si%'
    GROUP BY status
    ORDER BY COUNT DESC
    LIMIT 20;

             status          |  count
    -------------------------+----------
     success                 | 14143967
     no-pdf-link             | 12857899
     no-capture              |  5501279
     redirect-loop           |  2092667
     terminal-bad-status     |   747387
     wrong-mimetype          |   597212
     link-loop               |   542143
     null-body               |    93566
     cdx-error               |    20514
     petabox-error           |    18387
                             |    15283
     wayback-error           |    13996
     gateway-timeout         |      510
     skip-url-blocklist      |      184
     wayback-content-error   |      145
     bad-redirect            |      137
     redirects-exceeded      |      120
     bad-gzip-encoding       |      116
     timeout                 |       80
     spn2-cdx-lookup-failure |       58
    (20 rows)


    SELECT
        oai_prefix,
        COUNT(CASE WHEN status = 'success' THEN 1 END) as success,
        COUNT(*) as total
    FROM (
        SELECT
            ingest_file_result.status as status,
            -- eg "oai:cwi.nl:4881"
            substring(ingest_request.link_source_id FROM 'oai:([^:]+):.*') AS oai_prefix
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
            AND ingest_request.base_url NOT LIKE '%www.kb.dk%'
            AND ingest_request.base_url NOT LIKE '%kb-images.kb.dk%'
            AND ingest_request.base_url NOT LIKE '%mdz-nbn-resolving.de%'
            AND ingest_request.base_url NOT LIKE '%aggr.ukm.um.si%'
    ) t1
    GROUP BY oai_prefix
    ORDER BY total DESC
    LIMIT 25;

            oai_prefix        | success |  total  
    --------------------------+---------+---------
     repec                    | 1133019 | 2783448
     hal                      |  573019 | 1049607
     hsp.org                  |       0 |  810281
     www.irgrid.ac.cn         |   18007 |  748828
     cds.cern.ch              |   74078 |  688091
     americanae.aecid.es      |   71309 |  572792
     juser.fz-juelich.de      |   23026 |  518551
     espace.library.uq.edu.au |    6645 |  508960
     igi.indrastra.com        |   59626 |  478577
     archive.ugent.be         |   65269 |  424014
     hrcak.srce.hr            |  403719 |  414897
     zir.nsk.hr               |  156753 |  397200
     renati.sunedu.gob.pe     |   79362 |  388355
     hypotheses.org           |       3 |  374296
     rour.neicon.ru           |    7997 |  354529
     generic.eprints.org      |  263564 |  340470
     invenio.nusl.cz          |    6340 |  325867
     evastar-karlsruhe.de     |   62277 |  317952
     quod.lib.umich.edu       |       5 |  309135
     diva.org                 |   67917 |  298348
     t2r2.star.titech.ac.jp   |    1085 |  289388
     edpsciences.org          |  139495 |  284972
     repository.ust.hk        |   10243 |  283417
     revues.org               |  151156 |  277497
     pure.atira.dk            |   13492 |  260754
    (25 rows)

Top counts by OAI prefix and status:

    SELECT
        oai_prefix,
        status,
        COUNT((oai_prefix,status))
    FROM (
        SELECT
            ingest_file_result.status as status,
            -- eg "oai:cwi.nl:4881"
            substring(ingest_request.link_source_id FROM 'oai:([^:]+):.*') AS oai_prefix
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
            AND ingest_request.base_url NOT LIKE '%www.kb.dk%'
            AND ingest_request.base_url NOT LIKE '%kb-images.kb.dk%'
            AND ingest_request.base_url NOT LIKE '%mdz-nbn-resolving.de%'
            AND ingest_request.base_url NOT LIKE '%aggr.ukm.um.si%'
    ) t1
    GROUP BY oai_prefix, status
    ORDER BY COUNT DESC
    LIMIT 40;


            oai_prefix         |    status     |  count  
    ---------------------------+---------------+---------
     repec                     | success       | 1133019
     hsp.org                   | no-pdf-link   |  794781
     repec                     | no-pdf-link   |  638124
     hal                       | success       |  573020
     cds.cern.ch               | no-capture    |  540380
     repec                     | redirect-loop |  516434
     juser.fz-juelich.de       | no-pdf-link   |  477881
     americanae.aecid.es       | no-pdf-link   |  417766
     hrcak.srce.hr             | success       |  403720
     www.irgrid.ac.cn          | no-pdf-link   |  370908
     hal                       | no-pdf-link   |  359261
     www.irgrid.ac.cn          | no-capture    |  355532
     espace.library.uq.edu.au  | no-pdf-link   |  320479
     igi.indrastra.com         | no-pdf-link   |  318242
     repec                     | no-capture    |  317062
     invenio.nusl.cz           | no-pdf-link   |  309802
     rour.neicon.ru            | redirect-loop |  300911
     hypotheses.org            | no-pdf-link   |  300251
     renati.sunedu.gob.pe      | no-capture    |  282800
     t2r2.star.titech.ac.jp    | no-pdf-link   |  272045
     generic.eprints.org       | success       |  263564
     quod.lib.umich.edu        | no-pdf-link   |  259661
     archive.ugent.be          | no-capture    |  256164
     evastar-karlsruhe.de      | no-pdf-link   |  248939
     zir.nsk.hr                | link-loop     |  226919
     repository.ust.hk         | no-pdf-link   |  208569
     edoc.mpg.de               | no-pdf-link   |  199758
     bibliotecadigital.jcyl.es | no-pdf-link   |  188433
     orbi.ulg.ac.be            | no-pdf-link   |  172373
     diva.org                  | no-capture    |  171115
     lup.lub.lu.se             | no-pdf-link   |  168652
     erudit.org                | success       |  168490
     ojs.pkp.sfu.ca            | success       |  168029
     lib.dr.iastate.edu        | success       |  158494
     zir.nsk.hr                | success       |  156753
     digital.kenyon.edu        | success       |  154900
     revues.org                | success       |  151156
     books.openedition.org     | no-pdf-link   |  149607
     freidok.uni-freiburg.de   | no-pdf-link   |  146837
     digitalcommons.unl.edu    | success       |  144025
    (40 rows)

TODO: also exclude:

    oai:nsp.org:  (philly historical society)

TODO: more rows for success/total query (aka, increase LIMIT)

TODO: wait until MAG crawl is complete to re-run ingest? otherwise many
no-capture may actually be (recently) captured. depends on size of MAG crawl I
guess.

TODO: just delete the "excluded" rows?
TODO: do some spot-sampling of 'no-pdf-link' domains, see if newer sandcrawler works
TODO: do random sampling of 'no-pdf-link' URLs, see if newer sandcrawler works
