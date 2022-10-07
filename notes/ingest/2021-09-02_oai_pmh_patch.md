
Just a "patch" of previous OAI-PMH crawl/ingest: re-ingesting and potentially
re-crawling content which failed to ingest the first time.

May fold this in with more general patch crawling.

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
        AND ingest_request.link_source_id NOT LIKE 'oai:hsp.org:%'
        AND ingest_request.base_url NOT LIKE '%www.kb.dk%'
        AND ingest_request.base_url NOT LIKE '%kb-images.kb.dk%'
        AND ingest_request.base_url NOT LIKE '%mdz-nbn-resolving.de%'
        AND ingest_request.base_url NOT LIKE '%aggr.ukm.um.si%'
    GROUP BY status
    ORDER BY COUNT DESC
    LIMIT 20;

            status         |  count   
    -----------------------+----------
     success               | 14145387
     no-pdf-link           | 12063022
     no-capture            |  5485640
     redirect-loop         |  2092705
     terminal-bad-status   |   747372
     wrong-mimetype        |   597219
     link-loop             |   542144
     null-body             |    93566
     cdx-error             |    19798
     petabox-error         |    17943
                           |    15283
     wayback-error         |    13897
     gateway-timeout       |      511
     skip-url-blocklist    |      184
     wayback-content-error |      146
     bad-redirect          |      137
     redirects-exceeded    |      120
     bad-gzip-encoding     |      116
     timeout               |       80
     blocked-cookie        |       64
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
            AND ingest_request.link_source_id NOT LIKE 'oai:hsp.org:%'
            AND ingest_request.base_url NOT LIKE '%www.kb.dk%'
            AND ingest_request.base_url NOT LIKE '%kb-images.kb.dk%'
            AND ingest_request.base_url NOT LIKE '%mdz-nbn-resolving.de%'
            AND ingest_request.base_url NOT LIKE '%aggr.ukm.um.si%'
    ) t1
    GROUP BY oai_prefix
    ORDER BY total DESC
    LIMIT 40;


            oai_prefix         | success |  total
    ---------------------------+---------+---------
     repec                     | 1133175 | 2783448
     hal                       |  573218 | 1049607
     www.irgrid.ac.cn          |   18007 |  748828
     cds.cern.ch               |   74078 |  688091
     americanae.aecid.es       |   71310 |  572792
     juser.fz-juelich.de       |   23026 |  518551
     espace.library.uq.edu.au  |    6649 |  508960
     igi.indrastra.com         |   59629 |  478577
     archive.ugent.be          |   65306 |  424014
     hrcak.srce.hr             |  404085 |  414897
     zir.nsk.hr                |  156753 |  397200
     renati.sunedu.gob.pe      |   79362 |  388355
     hypotheses.org            |       3 |  374296
     rour.neicon.ru            |    7997 |  354529
     generic.eprints.org       |  263566 |  340470
     invenio.nusl.cz           |    6340 |  325867
     evastar-karlsruhe.de      |   62282 |  317952
     quod.lib.umich.edu        |       5 |  309135
     diva.org                  |   67917 |  298348
     t2r2.star.titech.ac.jp    |    1085 |  289388
     edpsciences.org           |  139495 |  284972
     repository.ust.hk         |   10245 |  283417
     revues.org                |  151156 |  277497
     pure.atira.dk             |   13492 |  260754
     bibliotecadigital.jcyl.es |   50606 |  254134
     escholarship.org/ark      |  140835 |  245203
     ojs.pkp.sfu.ca            |  168029 |  229387
     lup.lub.lu.se             |   49358 |  226602
     library.wur.nl            |   15051 |  216738
     digitalrepository.unm.edu |  111704 |  211749
     infoscience.tind.io       |   60166 |  207299
     edoc.mpg.de               |       0 |  205252
     erudit.org                |  168490 |  197803
     delibra.bg.polsl.pl       |   38666 |  196652
     n/a                       |       0 |  193814
     aleph.bib-bvb.de          |    4349 |  186666
     serval.unil.ch            |   41643 |  186372
     orbi.ulg.ac.be            |    2400 |  184551
     digitalcommons.unl.edu    |  144025 |  184372
     bib-pubdb1.desy.de        |   33525 |  182717
    (40 rows)

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
            AND ingest_request.link_source_id NOT LIKE 'oai:hsp.org:%'
            AND ingest_request.base_url NOT LIKE '%www.kb.dk%'
            AND ingest_request.base_url NOT LIKE '%kb-images.kb.dk%'
            AND ingest_request.base_url NOT LIKE '%mdz-nbn-resolving.de%'
            AND ingest_request.base_url NOT LIKE '%aggr.ukm.um.si%'
    ) t1
    GROUP BY oai_prefix, status
    ORDER BY COUNT DESC
    LIMIT 50;

            oai_prefix         |    status     |  count  
    ---------------------------+---------------+---------
     repec                     | success       | 1133175
     repec                     | no-pdf-link   |  638105
     hal                       | success       |  573218
     cds.cern.ch               | no-capture    |  540380
     repec                     | redirect-loop |  516451
     juser.fz-juelich.de       | no-pdf-link   |  477881
     americanae.aecid.es       | no-pdf-link   |  417766
     hrcak.srce.hr             | success       |  404085
     www.irgrid.ac.cn          | no-pdf-link   |  370908
     hal                       | no-pdf-link   |  359252
     www.irgrid.ac.cn          | no-capture    |  355532
     espace.library.uq.edu.au  | no-pdf-link   |  320479
     igi.indrastra.com         | no-pdf-link   |  318242
     repec                     | no-capture    |  316981
     invenio.nusl.cz           | no-pdf-link   |  309802
     rour.neicon.ru            | redirect-loop |  300911
     hypotheses.org            | no-pdf-link   |  300251
     renati.sunedu.gob.pe      | no-capture    |  282800
     t2r2.star.titech.ac.jp    | no-pdf-link   |  272045
     generic.eprints.org       | success       |  263566
     quod.lib.umich.edu        | no-pdf-link   |  259661
     archive.ugent.be          | no-capture    |  256127
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
     escholarship.org/ark      | success       |  140835
     culeuclid                 | link-loop     |  140291
     edpsciences.org           | success       |  139495
     serval.unil.ch            | no-pdf-link   |  138644
     bib-pubdb1.desy.de        | no-pdf-link   |  133815
     krm.or.kr                 | no-pdf-link   |  132461
     pure.atira.dk             | no-pdf-link   |  132179
     oai-gms.dimdi.de          | redirect-loop |  131409
     aleph.bib-bvb.de          | no-capture    |  128261
     library.wur.nl            | no-pdf-link   |  124718
     lirias2repo.kuleuven.be   | no-capture    |  123106
    (50 rows)

Note: could just delete the "excluded" rows? and not harvest them in the
future, and filter them at ingest time (in transform script).



## Investigate no-pdf-link sandcrawler improvements

Do some spot-sampling of 'no-pdf-link' domains, see if newer sandcrawler works:

    SELECT
        ingest_request.link_source_id AS oai_id,
        ingest_request.base_url as base_url ,
        ingest_file_result.terminal_url as terminal_url 
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
        AND ingest_request.base_url NOT LIKE '%www.kb.dk%'
        AND ingest_request.base_url NOT LIKE '%kb-images.kb.dk%'
        AND ingest_request.base_url NOT LIKE '%mdz-nbn-resolving.de%'
        AND ingest_request.base_url NOT LIKE '%aggr.ukm.um.si%'
        AND ingest_file_result.status = 'no-pdf-link'
        AND ingest_request.link_source_id LIKE 'oai:library.wur.nl:%'
    ORDER BY random()
    LIMIT 10;

Random sampling of *all* 'no-pdf-link' URLs (see if newer sandcrawler works):

    \x auto

    SELECT
        ingest_request.link_source_id AS oai_id,
        ingest_request.base_url as base_url ,
        ingest_file_result.terminal_url as terminal_url 
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
        AND ingest_request.base_url NOT LIKE '%www.kb.dk%'
        AND ingest_request.base_url NOT LIKE '%kb-images.kb.dk%'
        AND ingest_request.base_url NOT LIKE '%mdz-nbn-resolving.de%'
        AND ingest_request.base_url NOT LIKE '%aggr.ukm.um.si%'
        AND ingest_file_result.status = 'no-pdf-link'
    ORDER BY random()
    LIMIT 30;

### repec (SKIP-PREFIX)

-[ RECORD 1 ]+----------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:repec:eee:jmacro:v:54:y:2017:i:pb:p:332-351
base_url     | http://www.sciencedirect.com/science/article/pii/S0164070417301593
terminal_url | http://www.sciencedirect.com/science/article/pii/S0164070417301593
-[ RECORD 2 ]+----------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:repec:eee:jomega:v:16:y:1988:i:2:p:107-115
base_url     | http://www.sciencedirect.com/science/article/pii/0305-0483(88)90041-2
terminal_url | https://www.sciencedirect.com/science/article/abs/pii/0305048388900412
-[ RECORD 3 ]+----------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:repec:sgm:pzwzuw:v:14:i:59:y:2016:p:73-92
base_url     | http://pz.wz.uw.edu.pl/en
terminal_url | http://pz.wz.uw.edu.pl:80/en
-[ RECORD 1 ]+--------------------------------------------------------------------------------------------------------
--------------------------------------
oai_id       | oai:repec:eee:jmacro:v:54:y:2017:i:pb:p:332-351
base_url     | http://www.sciencedirect.com/science/article/pii/S0164070417301593
terminal_url | http://www.sciencedirect.com/science/article/pii/S0164070417301593
-[ RECORD 2 ]+--------------------------------------------------------------------------------------------------------
--------------------------------------
oai_id       | oai:repec:eee:jomega:v:16:y:1988:i:2:p:107-115
base_url     | http://www.sciencedirect.com/science/article/pii/0305-0483(88)90041-2
terminal_url | https://www.sciencedirect.com/science/article/abs/pii/0305048388900412
-[ RECORD 3 ]+--------------------------------------------------------------------------------------------------------
--------------------------------------
oai_id       | oai:repec:sgm:pzwzuw:v:14:i:59:y:2016:p:73-92
base_url     | http://pz.wz.uw.edu.pl/en
terminal_url | http://pz.wz.uw.edu.pl:80/en
-[ RECORD 4 ]+----------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:repec:erv:rccsrc:y:2016:i:2016_11:35
base_url     | http://www.eumed.net/rev/caribe/2016/11/estructura.html
terminal_url | http://www.eumed.net:80/rev/caribe/2016/11/estructura.html
-[ RECORD 5 ]+----------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:repec:pio:envira:v:33:y:2001:i:4:p:629-647
base_url     | http://www.envplan.com/epa/fulltext/a33/a3319.pdf
terminal_url | http://uk.sagepub.com:80/en-gb/eur/pion-journals-published
-[ RECORD 6 ]+----------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:repec:tpr:qjecon:v:100:y:1985:i:3:p:651-75
base_url     | http://links.jstor.org/sici?sici=0033-5533%28198508%29100%3A3%3C651%3ATCOCEA%3E2.0.CO%3B2-2&origin=repec
terminal_url | https://www.jstor.org/stable/1884373

Huh! This is just a catalog of other domains. Should probably skip

DONE: skip/filter repec

### juser.fz-juelich.de (SCOPE)

-[ RECORD 1 ]+------------------------------------------------------------
oai_id       | oai:juser.fz-juelich.de:132217
base_url     | http://juser.fz-juelich.de/record/132217
terminal_url | http://juser.fz-juelich.de/record/132217

Poster; no files.

-[ RECORD 2 ]+------------------------------------------------------------
oai_id       | oai:juser.fz-juelich.de:268598
base_url     | http://juser.fz-juelich.de/record/268598
terminal_url | http://juser.fz-juelich.de/record/268598

Journal.

-[ RECORD 3 ]+------------------------------------------------------------
oai_id       | oai:juser.fz-juelich.de:126613
base_url     | http://juser.fz-juelich.de/record/126613
terminal_url | http://juser.fz-juelich.de/record/126613

-[ RECORD 4 ]+------------------------------------------------------------
oai_id       | oai:juser.fz-juelich.de:67362
base_url     | http://juser.fz-juelich.de/record/67362
terminal_url | http://juser.fz-juelich.de/record/67362
-[ RECORD 5 ]+------------------------------------------------------------
oai_id       | oai:juser.fz-juelich.de:869189
base_url     | http://juser.fz-juelich.de/record/869189
terminal_url | http://juser.fz-juelich.de/record/869189
-[ RECORD 6 ]+------------------------------------------------------------
oai_id       | oai:juser.fz-juelich.de:810746
base_url     | http://juser.fz-juelich.de/record/810746
terminal_url | http://juser.fz-juelich.de/record/810746
-[ RECORD 7 ]+------------------------------------------------------------
oai_id       | oai:juser.fz-juelich.de:52897
base_url     | http://juser.fz-juelich.de/search?p=id:%22PreJuSER-52897%22
terminal_url | http://juser.fz-juelich.de/search?p=id:%22PreJuSER-52897%22
-[ RECORD 8 ]+------------------------------------------------------------
oai_id       | oai:juser.fz-juelich.de:114755
base_url     | http://juser.fz-juelich.de/record/114755
terminal_url | http://juser.fz-juelich.de/record/114755
-[ RECORD 9 ]+------------------------------------------------------------
oai_id       | oai:juser.fz-juelich.de:58025
base_url     | http://juser.fz-juelich.de/search?p=id:%22PreJuSER-58025%22
terminal_url | http://juser.fz-juelich.de/search?p=id:%22PreJuSER-58025%22

The search URLs seem redundant? Not going to try to handle those.

"Powered by Invenio v1.1.7"

All of these examples seem to be not papers. Maybe we can filter these better
at the harvest or transform stage?

### americanae.aecid.es (MIXED)

-[ RECORD 1 ]+---------------------------------------------------------------------------------------------
oai_id       | oai:americanae.aecid.es:502896
base_url     | http://biblioteca.clacso.edu.ar/gsdl/cgi-bin/library.cgi?a=d&c=mx/mx-010&d=60327292007oai
terminal_url | http://biblioteca.clacso.edu.ar/gsdl/cgi-bin/library.cgi?a=d&c=mx/mx-010&d=60327292007oai

just a metadata record? links to redalyc

METADATA-ONLY

-[ RECORD 2 ]+---------------------------------------------------------------------------------------------
oai_id       | oai:americanae.aecid.es:534600
base_url     | http://bdh-rd.bne.es/viewer.vm?id=0000077778&page=1
terminal_url | http://bdh-rd.bne.es/viewer.vm?id=0000077778&page=1
-[ RECORD 3 ]+---------------------------------------------------------------------------------------------
oai_id       | oai:americanae.aecid.es:524567
base_url     | http://americanae.aecid.es/americanae/es/registros/registro.do?tipoRegistro=MTD&idBib=524567
terminal_url | http://americanae.aecid.es/americanae/es/registros/registro.do?tipoRegistro=MTD&idBib=524567

NOT-FOUND (404)

-[ RECORD 4 ]+---------------------------------------------------------------------------------------------
oai_id       | oai:americanae.aecid.es:378914
base_url     | http://americanae.aecid.es/americanae/es/registros/registro.do?tipoRegistro=MTD&idBib=378914
terminal_url | http://americanae.aecid.es/americanae/es/registros/registro.do?tipoRegistro=MTD&idBib=378914

Some single-page image archival thing? bespoke, skipping.

SKIP-BESPOKE

-[ RECORD 5 ]+---------------------------------------------------------------------------------------------
oai_id       | oai:americanae.aecid.es:526142
base_url     | http://americanae.aecid.es/americanae/es/registros/registro.do?tipoRegistro=MTD&idBib=526142
terminal_url | http://americanae.aecid.es/americanae/es/registros/registro.do?tipoRegistro=MTD&idBib=526142

NOT-FOUND (404)

-[ RECORD 6 ]+---------------------------------------------------------------------------------------------
oai_id       | oai:americanae.aecid.es:373408
base_url     | http://americanae.aecid.es/americanae/es/registros/registro.do?tipoRegistro=MTD&idBib=373408
terminal_url | http://americanae.aecid.es/americanae/es/registros/registro.do?tipoRegistro=MTD&idBib=373408

NOT-FOUND (404)

### www.irgrid.ac.cn (SKIP-PREFIX)

Chinese Academy of Sciences Institutional Repositories Grid

-[ RECORD 1 ]+---------------------------------------------
oai_id       | oai:www.irgrid.ac.cn:1471x/1749980
base_url     | http://www.irgrid.ac.cn/handle/1471x/1749980
terminal_url | http://www.irgrid.ac.cn/handle/1471x/1749980

Can't access

FORBIDDEN

-[ RECORD 2 ]+---------------------------------------------
oai_id       | oai:www.irgrid.ac.cn:1471x/857397
base_url     | http://www.irgrid.ac.cn/handle/1471x/857397
terminal_url | http://www.irgrid.ac.cn/handle/1471x/857397

Just linking to another IR; skip it.

http://ir.ipe.ac.cn/handle/122111/10608

requires login

DONE: '/password-login;jsessionid' as a loginwall URL pattern
    http://ir.ipe.ac.cn/handle/122111/10608
    http://ir.ipe.ac.cn/bitstream/122111/10608/2/%e9%92%9d%e9%a1%b6%e8%9e%ba%e6%97%8b%e8%97%bb%e5%9c%a8%e4%b8%8d%e5%90%8c%e5%85%89%e7%85%a7%e6%9d%a1%e4%bb%b6%e4%b8%8b%e7%9a%84%e6%94%be%e6%b0%a7%e7%89%b9%e6%80%a7_%e8%96%9b%e5%8d%87%e9%95%bf.pdf

-[ RECORD 3 ]+---------------------------------------------
oai_id       | oai:www.irgrid.ac.cn:1471x/1060447
base_url     | http://www.irgrid.ac.cn/handle/1471x/1060447
terminal_url | http://www.irgrid.ac.cn/handle/1471x/1060447
-[ RECORD 4 ]+---------------------------------------------
oai_id       | oai:www.irgrid.ac.cn:1471x/1671377
base_url     | http://ir.iggcas.ac.cn/handle/132A11/68622
terminal_url | http://ir.iggcas.ac.cn/handle/132A11/68622
-[ RECORD 5 ]+---------------------------------------------
oai_id       | oai:www.irgrid.ac.cn:1471x/1178430
base_url     | http://www.irgrid.ac.cn/handle/1471x/1178430
terminal_url | http://www.irgrid.ac.cn/handle/1471x/1178430
-[ RECORD 6 ]+---------------------------------------------
oai_id       | oai:www.irgrid.ac.cn:1471x/2488017
base_url     | http://www.irgrid.ac.cn/handle/1471x/2488017
terminal_url | http://www.irgrid.ac.cn/handle/1471x/2488017
-[ RECORD 7 ]+---------------------------------------------
oai_id       | oai:www.irgrid.ac.cn:1471x/977147
base_url     | http://www.irgrid.ac.cn/handle/1471x/977147
terminal_url | http://www.irgrid.ac.cn/handle/1471x/977147
-[ RECORD 8 ]+---------------------------------------------
oai_id       | oai:www.irgrid.ac.cn:1471x/2454503
base_url     | http://ir.nwipb.ac.cn/handle/363003/9957
terminal_url | http://ir.nwipb.ac.cn/handle/363003/9957

this domain is a disapointment :(

should continue crawling, as the metadata is open and good. but won't get fulltext?

### hal (FIXED-PARTIAL)

-[ RECORD 1 ]+------------------------------------------------------------------------------
oai_id       | oai:hal:hal-00744951v1
base_url     | https://hal.archives-ouvertes.fr/hal-00744951
terminal_url | https://hal.archives-ouvertes.fr/hal-00744951

Off-site OA link.

FIXED-HAL

-[ RECORD 2 ]+------------------------------------------------------------------------------
oai_id       | oai:hal:hal-01065398v1
base_url     | https://hal.archives-ouvertes.fr/hal-01065398/file/AbstractSGE14_B_assaad.pdf
terminal_url | https://hal.archives-ouvertes.fr/index/index
-[ RECORD 3 ]+------------------------------------------------------------------------------
oai_id       | oai:hal:lirmm-00371599v1
base_url     | https://hal-lirmm.ccsd.cnrs.fr/lirmm-00371599
terminal_url | https://hal-lirmm.ccsd.cnrs.fr/lirmm-00371599

To elsevier :(

-[ RECORD 4 ]+------------------------------------------------------------------------------
oai_id       | oai:hal:hal-00284780v1
base_url     | https://hal.archives-ouvertes.fr/hal-00284780
terminal_url | https://hal.archives-ouvertes.fr/hal-00284780

METADATA-ONLY

-[ RECORD 5 ]+------------------------------------------------------------------------------
oai_id       | oai:hal:hal-00186151v1
base_url     | https://hal.archives-ouvertes.fr/hal-00186151
terminal_url | https://hal.archives-ouvertes.fr/hal-00186151

METADATA-ONLY

-[ RECORD 6 ]+------------------------------------------------------------------------------
oai_id       | oai:hal:hal-00399754v1
base_url     | https://hal.archives-ouvertes.fr/hal-00399754
terminal_url | https://hal.archives-ouvertes.fr/hal-00399754

METADATA-ONLY


### espace.library.uq.edu.au (SKIP)

-[ RECORD 1 ]+------------------------------------------------
oai_id       | oai:espace.library.uq.edu.au:uq:136497
base_url     | https://espace.library.uq.edu.au/view/UQ:136497
terminal_url | https://espace.library.uq.edu.au/view/UQ:136497
-[ RECORD 2 ]+------------------------------------------------
oai_id       | oai:espace.library.uq.edu.au:uq:411389
base_url     | https://espace.library.uq.edu.au/view/UQ:411389
terminal_url | https://espace.library.uq.edu.au/view/UQ:411389
-[ RECORD 3 ]+------------------------------------------------
oai_id       | oai:espace.library.uq.edu.au:uq:401773
base_url     | https://espace.library.uq.edu.au/view/UQ:401773
terminal_url | https://espace.library.uq.edu.au/view/UQ:401773
-[ RECORD 4 ]+------------------------------------------------
oai_id       | oai:espace.library.uq.edu.au:uq:675334
base_url     | https://espace.library.uq.edu.au/view/UQ:675334
terminal_url | https://espace.library.uq.edu.au/view/UQ:675334
-[ RECORD 5 ]+------------------------------------------------
oai_id       | oai:espace.library.uq.edu.au:uq:312311
base_url     | https://espace.library.uq.edu.au/view/UQ:312311
terminal_url | https://espace.library.uq.edu.au/view/UQ:312311
-[ RECORD 6 ]+------------------------------------------------
oai_id       | oai:espace.library.uq.edu.au:uq:209401
base_url     | https://espace.library.uq.edu.au/view/UQ:209401
terminal_url | https://espace.library.uq.edu.au/view/UQ:209401
-[ RECORD 7 ]+------------------------------------------------
oai_id       | oai:espace.library.uq.edu.au:uq:327188
base_url     | https://espace.library.uq.edu.au/view/UQ:327188
terminal_url | https://espace.library.uq.edu.au/view/UQ:327188

Very javascript heavy (skeletal HTML). And just links to fulltext on publisher
sites.

### igi.indrastra.com (METADATA-ONLY)

-[ RECORD 1 ]+---------------------------------------------------------
oai_id       | oai:igi.indrastra.com:267221
base_url     | http://igi.indrastra.com/items/show/267221
terminal_url | http://igi.indrastra.com/items/show/267221
-[ RECORD 2 ]+---------------------------------------------------------
oai_id       | oai:igi.indrastra.com:181799
base_url     | http://igi.indrastra.com/items/show/181799
terminal_url | http://igi.indrastra.com/items/show/181799
-[ RECORD 3 ]+---------------------------------------------------------
oai_id       | oai:igi.indrastra.com:125382
base_url     | http://igi.indrastra.com/items/show/125382
terminal_url | http://igi.indrastra.com/items/show/125382
-[ RECORD 4 ]+---------------------------------------------------------
oai_id       | oai:igi.indrastra.com:47266
base_url     | http://igi.indrastra.com/items/show/47266
terminal_url | http://igi.indrastra.com/items/show/47266
-[ RECORD 5 ]+---------------------------------------------------------
oai_id       | oai:igi.indrastra.com:12872
base_url     | http://igi.indrastra.com/items/show/12872
terminal_url | http://igi.indrastra.com/items/show/12872
-[ RECORD 6 ]+---------------------------------------------------------
oai_id       | oai:igi.indrastra.com:231620
base_url     | http://igi.indrastra.com/items/show/231620
terminal_url | http://igi.indrastra.com/items/show/231620

"Proudly powered by Omeka"

### invenio.nusl.cz (METADATA-ONLY)

           oai_id           |              base_url              |             terminal_url
----------------------------+------------------------------------+--------------------------------------
 oai:invenio.nusl.cz:237409 | http://www.nusl.cz/ntk/nusl-237409 | http://invenio.nusl.cz/record/237409
 oai:invenio.nusl.cz:180783 | http://www.nusl.cz/ntk/nusl-180783 | http://invenio.nusl.cz/record/180783
 oai:invenio.nusl.cz:231961 | http://www.nusl.cz/ntk/nusl-231961 | http://invenio.nusl.cz/record/231961
 oai:invenio.nusl.cz:318800 | http://www.nusl.cz/ntk/nusl-318800 | http://invenio.nusl.cz/record/318800
 oai:invenio.nusl.cz:259695 | http://www.nusl.cz/ntk/nusl-259695 | http://invenio.nusl.cz/record/259695
 oai:invenio.nusl.cz:167393 | http://www.nusl.cz/ntk/nusl-167393 | http://invenio.nusl.cz/record/167393
 oai:invenio.nusl.cz:292987 | http://www.nusl.cz/ntk/nusl-292987 | http://invenio.nusl.cz/record/292987
 oai:invenio.nusl.cz:283396 | http://www.nusl.cz/ntk/nusl-283396 | http://invenio.nusl.cz/record/283396
 oai:invenio.nusl.cz:241512 | http://www.nusl.cz/ntk/nusl-241512 | http://invenio.nusl.cz/record/241512
 oai:invenio.nusl.cz:178631 | http://www.nusl.cz/ntk/nusl-178631 | http://invenio.nusl.cz/record/178631

Metadata only (at least this set)

### hypotheses.org

-[ RECORD 1 ]+---------------------------------------------
oai_id       | oai:hypotheses.org:mittelalter/9529
base_url     | http://mittelalter.hypotheses.org/9529
terminal_url | https://mittelalter.hypotheses.org/9529
-[ RECORD 2 ]+---------------------------------------------
oai_id       | oai:hypotheses.org:archivalia/18638
base_url     | http://archivalia.hypotheses.org/18638
terminal_url | https://archivalia.hypotheses.org/18638
-[ RECORD 3 ]+---------------------------------------------
oai_id       | oai:hypotheses.org:archivalia/13614
base_url     | http://archivalia.hypotheses.org/13614
terminal_url | https://archivalia.hypotheses.org/13614
-[ RECORD 4 ]+---------------------------------------------
oai_id       | oai:hypotheses.org:teteschercheuses/2785
base_url     | http://teteschercheuses.hypotheses.org/2785
terminal_url | https://teteschercheuses.hypotheses.org/2785
-[ RECORD 5 ]+---------------------------------------------
oai_id       | oai:hypotheses.org:altervsego/608
base_url     | http://altervsego.hypotheses.org/608
terminal_url | http://altervsego.hypotheses.org/608
-[ RECORD 6 ]+---------------------------------------------
oai_id       | oai:hypotheses.org:archivewk1/21905
base_url     | http://archivewk1.hypotheses.org/21905
terminal_url | https://archivewk1.hypotheses.org/21905
-[ RECORD 7 ]+---------------------------------------------
oai_id       | oai:hypotheses.org:slkdiaspo/3321
base_url     | http://slkdiaspo.hypotheses.org/3321
terminal_url | https://slkdiaspo.hypotheses.org/3321
-[ RECORD 8 ]+---------------------------------------------
oai_id       | oai:hypotheses.org:diga/280
base_url     | http://diga.hypotheses.org/280
terminal_url | https://diga.hypotheses.org/280

These are all a big mix... basically blogs. Should continue crawling, but expect no yield.

### t2r2.star.titech.ac.jp (METADATA-ONLY)

-[ RECORD 1 ]+----------------------------------------------------------------------------------------------------
oai_id       | oai:t2r2.star.titech.ac.jp:00105099
base_url     | http://t2r2.star.titech.ac.jp/cgi-bin/publicationinfo.cgi?q_publication_content_number=CTT100499795
terminal_url | http://t2r2.star.titech.ac.jp/cgi-bin/publicationinfo.cgi?q_publication_content_number=CTT100499795
-[ RECORD 2 ]+----------------------------------------------------------------------------------------------------
oai_id       | oai:t2r2.star.titech.ac.jp:00101346
base_url     | http://t2r2.star.titech.ac.jp/cgi-bin/publicationinfo.cgi?q_publication_content_number=CTT100495549
terminal_url | http://t2r2.star.titech.ac.jp/cgi-bin/publicationinfo.cgi?q_publication_content_number=CTT100495549
-[ RECORD 3 ]+----------------------------------------------------------------------------------------------------
oai_id       | oai:t2r2.star.titech.ac.jp:50161100
base_url     | http://t2r2.star.titech.ac.jp/cgi-bin/publicationinfo.cgi?q_publication_content_number=CTT100632554
terminal_url | http://t2r2.star.titech.ac.jp/cgi-bin/publicationinfo.cgi?q_publication_content_number=CTT100632554
-[ RECORD 4 ]+----------------------------------------------------------------------------------------------------
oai_id       | oai:t2r2.star.titech.ac.jp:00232407
base_url     | http://t2r2.star.titech.ac.jp/cgi-bin/publicationinfo.cgi?q_publication_content_number=CTT100527528
terminal_url | http://t2r2.star.titech.ac.jp/cgi-bin/publicationinfo.cgi?q_publication_content_number=CTT100527528
-[ RECORD 5 ]+----------------------------------------------------------------------------------------------------
oai_id       | oai:t2r2.star.titech.ac.jp:50120040
base_url     | http://t2r2.star.titech.ac.jp/cgi-bin/publicationinfo.cgi?q_publication_content_number=CTT100612598
terminal_url | http://t2r2.star.titech.ac.jp/cgi-bin/publicationinfo.cgi?q_publication_content_number=CTT100612598
-[ RECORD 6 ]+----------------------------------------------------------------------------------------------------
oai_id       | oai:t2r2.star.titech.ac.jp:50321440
base_url     | http://t2r2.star.titech.ac.jp/cgi-bin/publicationinfo.cgi?q_publication_content_number=CTT100713492
terminal_url | http://t2r2.star.titech.ac.jp/cgi-bin/publicationinfo.cgi?q_publication_content_number=CTT100713492
-[ RECORD 7 ]+----------------------------------------------------------------------------------------------------
oai_id       | oai:t2r2.star.titech.ac.jp:50235666
base_url     | http://t2r2.star.titech.ac.jp/cgi-bin/publicationinfo.cgi?q_publication_content_number=CTT100668778
terminal_url | http://t2r2.star.titech.ac.jp/cgi-bin/publicationinfo.cgi?q_publication_content_number=CTT100668778


### quod.lib.umich.edu

-[ RECORD 1 ]+-------------------------------------------------------------------------------------------------------
oai_id       | oai:quod.lib.umich.edu:acf2679.0015.003-2
base_url     | http://name.umdl.umich.edu/acf2679.0015.003
terminal_url | https://quod.lib.umich.edu/cgi/t/text/text-idx?c=moajrnl;idno=acf2679.0015.003
-[ RECORD 2 ]+-------------------------------------------------------------------------------------------------------
oai_id       | oai:quod.lib.umich.edu:b14970.0001.001
base_url     | http://name.umdl.umich.edu/B14970.0001.001
terminal_url | https://quod.lib.umich.edu/cgi/t/text/text-idx?c=eebo2;idno=B14970.0001.001
-[ RECORD 3 ]+-------------------------------------------------------------------------------------------------------
oai_id       | oai:quod.lib.umich.edu:acf2679.0009.010-3
base_url     | http://name.umdl.umich.edu/ACF2679-1623SOUT-209
terminal_url | https://quod.lib.umich.edu/cgi/t/text/text-idx?c=moajrnl;idno=acf2679.0009.010;node=acf2679.0009.010:3
-[ RECORD 4 ]+-------------------------------------------------------------------------------------------------------
oai_id       | oai:quod.lib.umich.edu:acg2248.1-16.006-43
base_url     | http://name.umdl.umich.edu/acg2248.1-16.006
terminal_url | https://quod.lib.umich.edu/cgi/t/text/text-idx?c=moajrnl;idno=acg2248.1-16.006
-[ RECORD 5 ]+-------------------------------------------------------------------------------------------------------
oai_id       | oai:quod.lib.umich.edu:acg2248.1-14.011-9
base_url     | http://name.umdl.umich.edu/ACG2248-1489LADI-364
terminal_url | https://quod.lib.umich.edu/cgi/t/text/text-idx?c=moajrnl;idno=acg2248.1-14.011;node=acg2248.1-14.011:9
-[ RECORD 6 ]+-------------------------------------------------------------------------------------------------------
oai_id       | oai:quod.lib.umich.edu:acg1336.1-24.006-9
base_url     | http://name.umdl.umich.edu/acg1336.1-24.006
terminal_url | https://quod.lib.umich.edu/cgi/t/text/text-idx?c=moajrnl;idno=acg1336.1-24.006
-[ RECORD 7 ]+-------------------------------------------------------------------------------------------------------
oai_id       | oai:quod.lib.umich.edu:africanamer.0002.32a
base_url     | http://name.umdl.umich.edu/africanamer.0002.32a
terminal_url | https://quod.lib.umich.edu/cgi/t/text/text-idx?c=africanamer;idno=africanamer.0002.32a

These are... issues of journals? Should continue to crawl, but not expect much.

### evastar-karlsruhe.de (METADATA-ONLY)

-[ RECORD 1 ]+----------------------------------------------------
oai_id       | oai:evastar-karlsruhe.de:270011444
base_url     | https://publikationen.bibliothek.kit.edu/270011444
terminal_url | https://publikationen.bibliothek.kit.edu/270011444
-[ RECORD 2 ]+----------------------------------------------------
oai_id       | oai:evastar-karlsruhe.de:1000050117
base_url     | https://publikationen.bibliothek.kit.edu/1000050117
terminal_url | https://publikationen.bibliothek.kit.edu/1000050117
-[ RECORD 3 ]+----------------------------------------------------
oai_id       | oai:evastar-karlsruhe.de:362296
base_url     | https://publikationen.bibliothek.kit.edu/362296
terminal_url | https://publikationen.bibliothek.kit.edu/362296
-[ RECORD 4 ]+----------------------------------------------------
oai_id       | oai:evastar-karlsruhe.de:23042000
base_url     | https://publikationen.bibliothek.kit.edu/23042000
terminal_url | https://publikationen.bibliothek.kit.edu/23042000
-[ RECORD 5 ]+----------------------------------------------------
oai_id       | oai:evastar-karlsruhe.de:1000069945
base_url     | https://publikationen.bibliothek.kit.edu/1000069945
terminal_url | https://publikationen.bibliothek.kit.edu/1000069945


### repository.ust.hk

-[ RECORD 1 ]+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:repository.ust.hk:1783.1-67233
base_url     | http://repository.ust.hk/ir/Record/1783.1-67233
terminal_url | http://repository.ust.hk/ir/Record/1783.1-67233
-[ RECORD 2 ]+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:repository.ust.hk:1783.1-63232
base_url     | http://gateway.isiknowledge.com/gateway/Gateway.cgi?GWVersion=2&SrcAuth=LinksAMR&SrcApp=PARTNER_APP&DestLinkType=FullRecord&DestApp=WOS&KeyUT=A1981KV47900017
terminal_url | http://login.webofknowledge.com/error/Error?Src=IP&Alias=WOK5&Error=IPError&Params=DestParams%3D%253FUT%253DWOS%253AA1981KV47900017%2526customersID%253DLinksAMR%2526product%253DWOS%2526action%253Dretrieve%2526mode%253DFullRecord%26DestApp%3DWOS%26SrcApp%3DPARTNER_APP%26SrcAuth%3DLinksAMR&PathInfo=%2F&RouterURL=http%3A%2F%2Fwww.webofknowledge.com%2F&Domain=.webofknowledge.com
-[ RECORD 3 ]+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:repository.ust.hk:1783.1-2891
base_url     | http://gateway.isiknowledge.com/gateway/Gateway.cgi?GWVersion=2&SrcAuth=LinksAMR&SrcApp=PARTNER_APP&DestLinkType=FullRecord&DestApp=WOS&KeyUT=000240035400103
terminal_url | https://login.webofknowledge.com/error/Error?Src=IP&Alias=WOK5&Error=IPError&Params=DestParams%3D%253FUT%253DWOS%253A000240035400103%2526customersID%253DLinksAMR%2526product%253DWOS%2526action%253Dretrieve%2526mode%253DFullRecord%26DestApp%3DWOS%26SrcApp%3DPARTNER_APP%26SrcAuth%3DLinksAMR&PathInfo=%2F&RouterURL=https%3A%2F%2Fwww.webofknowledge.com%2F&Domain=.webofknowledge.com
-[ RECORD 4 ]+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:repository.ust.hk:1783.1-56231
base_url     | http://repository.ust.hk/ir/Record/1783.1-56231
terminal_url | http://repository.ust.hk/ir/Record/1783.1-56231

[...]

-[ RECORD 6 ]+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:repository.ust.hk:1783.1-24872
base_url     | http://repository.ust.hk/ir/Record/1783.1-24872
terminal_url | http://repository.ust.hk/ir/Record/1783.1-24872
-[ RECORD 7 ]+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:repository.ust.hk:1783.1-3457
base_url     | http://lbdiscover.ust.hk/uresolver?url_ver=Z39.88-2004&rft_val_fmt=info:ofi/fmt:kev:mtx:journal&rfr_id=info:sid/HKUST:SPI&rft.genre=article&rft.issn=0003-6870&rft.volume=40&rft.issue=2&rft.date=2009&rft.spage=267&rft.epage=279&rft.aulast=Witana&rft.aufirst=Channa+R.&rft.atitle=Effects+of+surface+characteristics+on+the+plantar+shape+of+feet+and+subjects'+perceived+sensations
terminal_url | http://lbdiscover.ust.hk/uresolver/?url_ver=Z39.88-2004&rft_val_fmt=info:ofi/fmt:kev:mtx:journal&rfr_id=info:sid/HKUST:SPI&rft.genre=article&rft.issn=0003-6870&rft.volume=40&rft.issue=2&rft.date=2009&rft.spage=267&rft.epage=279&rft.aulast=Witana&rft.aufirst=Channa+R.&rft.atitle=Effects+of+surface+characteristics+on+the+plantar+shape+of+feet+and+subjects'+perceived+sensations
-[ RECORD 8 ]+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:repository.ust.hk:1783.1-73215
base_url     | http://repository.ust.hk/ir/Record/1783.1-73215
terminal_url | http://repository.ust.hk/ir/Record/1783.1-73215

DONE: gateway.isiknowledge.com is bogus/blocking?


### edoc.mpg.de (SKIP-DEPRECATED)

         oai_id         |         base_url          |       terminal_url
------------------------+---------------------------+---------------------------
 oai:edoc.mpg.de:416650 | http://edoc.mpg.de/416650 | http://edoc.mpg.de/416650
 oai:edoc.mpg.de:8195   | http://edoc.mpg.de/8195   | http://edoc.mpg.de/8195
 oai:edoc.mpg.de:379655 | http://edoc.mpg.de/379655 | http://edoc.mpg.de/379655
 oai:edoc.mpg.de:641179 | http://edoc.mpg.de/641179 | http://edoc.mpg.de/641179
 oai:edoc.mpg.de:607141 | http://edoc.mpg.de/607141 | http://edoc.mpg.de/607141
 oai:edoc.mpg.de:544412 | http://edoc.mpg.de/544412 | http://edoc.mpg.de/544412
 oai:edoc.mpg.de:314531 | http://edoc.mpg.de/314531 | http://edoc.mpg.de/314531
 oai:edoc.mpg.de:405047 | http://edoc.mpg.de/405047 | http://edoc.mpg.de/405047
 oai:edoc.mpg.de:239650 | http://edoc.mpg.de/239650 | http://edoc.mpg.de/239650
 oai:edoc.mpg.de:614852 | http://edoc.mpg.de/614852 | http://edoc.mpg.de/614852

This whole instance seems to have been replaced

### bibliotecadigital.jcyl.es (SKIP-DIGITIZED)

-[ RECORD 1 ]+--------------------------------------------------------------------------------
oai_id       | oai:bibliotecadigital.jcyl.es:10000039962
base_url     | http://bibliotecadigital.jcyl.es/i18n/catalogo_imagenes/grupo.cmd?path=10044664
terminal_url | http://bibliotecadigital.jcyl.es/i18n/catalogo_imagenes/grupo.cmd?path=10044664
-[ RECORD 2 ]+--------------------------------------------------------------------------------
oai_id       | oai:bibliotecadigital.jcyl.es:14075
base_url     | http://bibliotecadigital.jcyl.es/i18n/consulta/registro.cmd?id=14075
terminal_url | http://bibliotecadigital.jcyl.es/i18n/consulta/registro.cmd?id=14075
-[ RECORD 3 ]+--------------------------------------------------------------------------------
oai_id       | oai:bibliotecadigital.jcyl.es:4842
base_url     | http://bibliotecadigital.jcyl.es/i18n/consulta/registro.cmd?id=4842
terminal_url | http://bibliotecadigital.jcyl.es/i18n/consulta/registro.cmd?id=4842
-[ RECORD 4 ]+--------------------------------------------------------------------------------
oai_id       | oai:bibliotecadigital.jcyl.es:14799
base_url     | http://bibliotecadigital.jcyl.es/i18n/consulta/registro.cmd?id=14799
terminal_url | http://bibliotecadigital.jcyl.es/i18n/consulta/registro.cmd?id=14799
-[ RECORD 5 ]+--------------------------------------------------------------------------------
oai_id       | oai:bibliotecadigital.jcyl.es:821
base_url     | http://bibliotecadigital.jcyl.es/i18n/catalogo_imagenes/grupo.cmd?path=1003474
terminal_url | http://bibliotecadigital.jcyl.es/i18n/catalogo_imagenes/grupo.cmd?path=1003474

Digitized images as pages; too much to deal with for now.

### orbi.ulg.ac.be

-[ RECORD 1 ]+----------------------------------------------------------------
oai_id       | oai:orbi.ulg.ac.be:2268/128079
base_url     | https://orbi.uliege.be/handle/2268/128079
terminal_url | https://orbi.uliege.be/handle/2268/128079
-[ RECORD 2 ]+----------------------------------------------------------------
oai_id       | oai:orbi.ulg.ac.be:2268/67659
base_url     | https://orbi.uliege.be/handle/2268/67659
terminal_url | https://orbi.uliege.be/handle/2268/67659
-[ RECORD 3 ]+----------------------------------------------------------------
oai_id       | oai:orbi.ulg.ac.be:2268/35521
base_url     | https://orbi.uliege.be/handle/2268/35521
terminal_url | https://orbi.uliege.be/handle/2268/35521
-[ RECORD 4 ]+----------------------------------------------------------------
oai_id       | oai:orbi.ulg.ac.be:2268/107922
base_url     | https://orbi.uliege.be/handle/2268/107922
terminal_url | https://orbi.uliege.be/handle/2268/107922
-[ RECORD 5 ]+----------------------------------------------------------------
oai_id       | oai:orbi.ulg.ac.be:2268/215694
base_url     | https://orbi.uliege.be/handle/2268/215694
terminal_url | https://orbi.uliege.be/handle/2268/215694

Described below.

### library.wur.nl (FIXED-BESPOKE)

                  oai_id               |                    base_url                    |                  terminal_url                  
    -----------------------------------+------------------------------------------------+------------------------------------------------
     oai:library.wur.nl:wurpubs/440939 | https://library.wur.nl/WebQuery/wurpubs/440939 | https://library.wur.nl/WebQuery/wurpubs/440939
     oai:library.wur.nl:wurpubs/427707 | https://library.wur.nl/WebQuery/wurpubs/427707 | https://library.wur.nl/WebQuery/wurpubs/427707
     oai:library.wur.nl:wurpubs/359208 | https://library.wur.nl/WebQuery/wurpubs/359208 | https://library.wur.nl/WebQuery/wurpubs/359208
     oai:library.wur.nl:wurpubs/433378 | https://library.wur.nl/WebQuery/wurpubs/433378 | https://library.wur.nl/WebQuery/wurpubs/433378
     oai:library.wur.nl:wurpubs/36416  | https://library.wur.nl/WebQuery/wurpubs/36416  | https://library.wur.nl/WebQuery/wurpubs/36416
     oai:library.wur.nl:wurpubs/469930 | https://library.wur.nl/WebQuery/wurpubs/469930 | https://library.wur.nl/WebQuery/wurpubs/469930
     oai:library.wur.nl:wurpubs/350076 | https://library.wur.nl/WebQuery/wurpubs/350076 | https://library.wur.nl/WebQuery/wurpubs/350076
     oai:library.wur.nl:wurpubs/19109  | https://library.wur.nl/WebQuery/wurpubs/19109  | https://library.wur.nl/WebQuery/wurpubs/19109
     oai:library.wur.nl:wurpubs/26146  | https://library.wur.nl/WebQuery/wurpubs/26146  | https://library.wur.nl/WebQuery/wurpubs/26146
     oai:library.wur.nl:wurpubs/529922 | https://library.wur.nl/WebQuery/wurpubs/529922 | https://library.wur.nl/WebQuery/wurpubs/529922
    (10 rows)

Seems like a one-off site? But added a pattern.

### pure.atira.dk

-[ RECORD 1 ]+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:pure.atira.dk:publications/a27762fd-0919-4753-af55-00b9b26d02e0
base_url     | https://www.research.manchester.ac.uk/portal/en/publications/hightech-cities-and-the-primitive-jungle-visionary-urbanism-in-europe-and-japan-of-the-1960s(a27762fd-0919-4753-af55-00b9b26d02e0).html
terminal_url | https://www.research.manchester.ac.uk/portal/en/publications/hightech-cities-and-the-primitive-jungle-visionary-urbanism-in-europe-and-japan-of-the-1960s(a27762fd-0919-4753-af55-00b9b26d02e0).html
-[ RECORD 2 ]+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:pure.atira.dk:publications/215c8b96-a821-4947-bee4-c7470e9fbaf8
base_url     | https://www.research.manchester.ac.uk/portal/en/publications/service-recovery-in-health-services--understanding-the-desired-qualities-and-behaviours-of-general-practitioners-during-service-recovery-encounters(215c8b96-a821-4947-bee4-c7470e9fbaf8).html
terminal_url | https://www.research.manchester.ac.uk/portal/en/publications/service-recovery-in-health-services--understanding-the-desired-qualities-and-behaviours-of-general-practitioners-during-service-recovery-encounters(215c8b96-a821-4947-bee4-c7470e9fbaf8).html
-[ RECORD 3 ]+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:pure.atira.dk:publications/95d4920a-12c7-4e25-b86c-5f075ea23a38
base_url     | https://www.tandfonline.com/doi/full/10.1080/03057070.2016.1197694
terminal_url | https://www.tandfonline.com/action/cookieAbsent
-[ RECORD 4 ]+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:pure.atira.dk:publications/8a2508ee-14c9-4c6a-851a-6db442090f41
base_url     | https://www.research.manchester.ac.uk/portal/en/publications/microstructure-and-grain-size-dependence-of-ferroelectric-properties-of-batio3-thin-films-on-lanio3-buffered-si(8a2508ee-14c9-4c6a-851a-6db442090f41).html
terminal_url | https://www.research.manchester.ac.uk/portal/en/publications/microstructure-and-grain-size-dependence-of-ferroelectric-properties-of-batio3-thin-films-on-lanio3-buffered-si(8a2508ee-14c9-4c6a-851a-6db442090f41).html

Metadata only

DONE: /cookieAbsent is cookie block
    https://www.tandfonline.com/action/cookieAbsent

### bib-pubdb1.desy.de (FIXED-INVENIO)

-[ RECORD 2 ]+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:bib-pubdb1.desy.de:96756
base_url     | http://bib-pubdb1.desy.de/record/96756
terminal_url | http://bib-pubdb1.desy.de/record/96756

Metadata only.

-[ RECORD 3 ]+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:bib-pubdb1.desy.de:416556
base_url     | http://bib-pubdb1.desy.de/record/416556
terminal_url | http://bib-pubdb1.desy.de/record/416556

Fixed!

-[ RECORD 4 ]+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:bib-pubdb1.desy.de:414545
base_url     | http://bib-pubdb1.desy.de/search?p=id:%22PUBDB-2018-04027%22
terminal_url | http://bib-pubdb1.desy.de/search?p=id:%22PUBDB-2018-04027%22
-[ RECORD 5 ]+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:bib-pubdb1.desy.de:170169
base_url     | http://bib-pubdb1.desy.de/record/170169
terminal_url | http://bib-pubdb1.desy.de/record/170169
-[ RECORD 6 ]+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:bib-pubdb1.desy.de:191154
base_url     | http://bib-pubdb1.desy.de/record/191154
terminal_url | http://bib-pubdb1.desy.de/record/191154

Metadata only

-[ RECORD 7 ]+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:bib-pubdb1.desy.de:155092
base_url     | http://bib-pubdb1.desy.de/record/155092
terminal_url | http://bib-pubdb1.desy.de/record/155092

Fixed!

-[ RECORD 8 ]+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:bib-pubdb1.desy.de:97158
base_url     | http://bib-pubdb1.desy.de/record/97158
terminal_url | http://bib-pubdb1.desy.de/record/97158

Metadata only

"Powered by Invenio v1.1.7"

Can/should skip the "search" URLs

### serval.unil.ch

-[ RECORD 1 ]+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:serval.unil.ch:bib_60346fc75171
base_url     | https://serval.unil.ch/notice/serval:BIB_60346FC75171
terminal_url | https://serval.unil.ch/en/notice/serval:BIB_60346FC75171
-[ RECORD 2 ]+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:serval.unil.ch:bib_4db47fc4b593
base_url     | https://serval.unil.ch/notice/serval:BIB_4DB47FC4B593
terminal_url | https://serval.unil.ch/en/notice/serval:BIB_4DB47FC4B593
-[ RECORD 3 ]+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:serval.unil.ch:bib_57aac24fe115
base_url     | http://nbn-resolving.org/urn/resolver.pl?urn=urn:nbn:ch:serval-BIB_57AAC24FE1154
terminal_url | https://nbn-resolving.org/urn/resolver.pl?urn=urn:nbn:ch:serval-BIB_57AAC24FE1154
-[ RECORD 4 ]+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:serval.unil.ch:bib_deabae6baf6c
base_url     | https://serval.unil.ch/notice/serval:BIB_DEABAE6BAF6C
terminal_url | https://serval.unil.ch/en/notice/serval:BIB_DEABAE6BAF6C
-[ RECORD 5 ]+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:serval.unil.ch:bib_a5ec0df1370f
base_url     | https://serval.unil.ch/notice/serval:BIB_A5EC0DF1370F
terminal_url | https://wayf.switch.ch/SWITCHaai/WAYF?entityID=https%3A%2F%2Fmy.unil.ch%2Fshibboleth&return=https%3A%2F%2Fserval.unil.ch%2FShibboleth.sso%2FLogin%3FSAMLDS%3D1%26target%3Dss%253Amem%253Aed270c26d4a36cefd1bf6a840472abe0ee5556cb5f3b42de708f3ea984775dfd
-[ RECORD 6 ]+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:serval.unil.ch:bib_080300c2e23c
base_url     | https://serval.unil.ch/resource/serval:BIB_080300C2E23C.P001/REF.pdf
terminal_url | https://wayf.switch.ch/SWITCHaai/WAYF?entityID=https%3A%2F%2Fmy.unil.ch%2Fshibboleth&return=https%3A%2F%2Fserval.unil.ch%2FShibboleth.sso%2FLogin%3FSAMLDS%3D1%26target%3Dss%253Amem%253A154453d78a0fb75ffa220f7b6fe73b29447fa6ed048addf31897b41001f44679
-[ RECORD 7 ]+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:serval.unil.ch:bib_de777dd2b07f
base_url     | https://serval.unil.ch/notice/serval:BIB_DE777DD2B07F
terminal_url | https://serval.unil.ch/en/notice/serval:BIB_DE777DD2B07F
-[ RECORD 8 ]+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:serval.unil.ch:bib_5e824e244c27
base_url     | https://serval.unil.ch/notice/serval:BIB_5E824E244C27
terminal_url | https://serval.unil.ch/en/notice/serval:BIB_5E824E244C27

Metadata only? See elsewhere.

### Random Links

-[ RECORD 1 ]+---------------------------------------------------------------------------------------------------------------------
oai_id       | oai:dbc.wroc.pl:41031
base_url     | https://dbc.wroc.pl/dlibra/docmetadata?showContent=true&id=41031
terminal_url | https://dbc.wroc.pl/dlibra/docmetadata?showContent=true&id=41031

This is some platform/package thing. PDF is in an iframe. Platform is "DLibra".
FIXED-DLIBRA

-[ RECORD 2 ]+---------------------------------------------------------------------------------------------------------------------
oai_id       | oai:orbi.ulg.ac.be:2268/174291
base_url     | https://orbi.uliege.be/handle/2268/174291
terminal_url | https://orbi.uliege.be/handle/2268/174291

DSpace platform. There are multiple files, and little to "select" on.

https://orbi.uliege.be/handle/2268/174200 has only single PDF and easier to work with

PARTIAL-DSPACE

-[ RECORD 3 ]+---------------------------------------------------------------------------------------------------------------------
oai_id       | oai:library.tue.nl:664163
base_url     | http://repository.tue.nl/664163
terminal_url | http://repository.tue.nl/664163

Ah, this is the Pure platform from Elsevier.
Redirects to: https://research.tue.nl/en/publications/lowering-the-threshold-for-computers-in-early-design-some-advance

FIXED-PURE


-[ RECORD 4 ]+---------------------------------------------------------------------------------------------------------------------
oai_id       | oai:juser.fz-juelich.de:49579
base_url     | http://juser.fz-juelich.de/search?p=id:%22PreJuSER-49579%22
terminal_url | http://juser.fz-juelich.de/search?p=id:%22PreJuSER-49579%22

(handled above)

-[ RECORD 5 ]+---------------------------------------------------------------------------------------------------------------------
oai_id       | oai:dspace.mit.edu:1721.1/97937
base_url     | https://orcid.org/0000-0002-2066-2082
terminal_url | https://orcid.org/0000-0002-2066-2082

ORCID! Skip it.

DONE: skip orcid.org in `terminal_url`, and/or at harvest/transform time.

-[ RECORD 6 ]+---------------------------------------------------------------------------------------------------------------------
oai_id       | oai:edoc.mpg.de:360269
base_url     | http://edoc.mpg.de/360269
terminal_url | http://edoc.mpg.de/360269

Seems like this whole repo has disapeared, or been replaced by... pure? maybe a different pure?

DONE: edoc.mpg.de -> pure.mpg.de

-[ RECORD 7 ]+---------------------------------------------------------------------------------------------------------------------
oai_id       | oai:books.openedition.org:msha/17716
base_url     | http://books.openedition.org/msha/17716
terminal_url | https://books.openedition.org/msha/17716

Open edition is free to read HTML, but not PDF (or epub, etc).

TODO: for some? all? openedition books records, try HTML ingest (not PDF ingest)

HTML-WORKED

-[ RECORD 8 ]+---------------------------------------------------------------------------------------------------------------------
oai_id       | oai:epub.oeaw.ac.at:0x003aba48
base_url     | http://epub.oeaw.ac.at/?arp=8609-0inhalt/B02_2146_FP_Flores%20Castillo.pdf
terminal_url | http://epub.oeaw.ac.at/?arp=8609-0inhalt/B02_2146_FP_Flores%20Castillo.pdf

requires login

FORBIDDEN

-[ RECORD 9 ]+---------------------------------------------------------------------------------------------------------------------
oai_id       | oai:dspace.mit.edu:1721.1/88986
base_url     | https://orcid.org/0000-0002-4147-2560
terminal_url | https://orcid.org/0000-0002-4147-2560

DONE: skip orcids

-[ RECORD 10 ]---------------------------------------------------------------------------------------------------------------------
oai_id       | oai:repository.ust.hk:1783.1-28786
base_url     | http://repository.ust.hk/ir/Record/1783.1-28786
terminal_url | http://repository.ust.hk/ir/Record/1783.1-28786

Generator: VuFind 5.1.1
just a metadata record

METADATA-ONLY

-[ RECORD 11 ]---------------------------------------------------------------------------------------------------------------------
oai_id       | oai:rcin.org.pl:50797
base_url     | http://195.187.71.10/ipac20/ipac.jsp?profile=iblpan&index=BOCLC&term=cc95215472
terminal_url | http://195.187.71.10/ipac20/ipac.jsp?profile=iblpan&index=BOCLC&term=cc95215472

Seems like a software platform? not sure.

METADATA-ONLY

-[ RECORD 12 ]---------------------------------------------------------------------------------------------------------------------
oai_id       | oai:dea.lib.unideb.hu:2437/69641
base_url     | http://webpac.lib.unideb.hu:8082/WebPac/CorvinaWeb?action=cclfind&amp;resultview=long&amp;ccltext=idno+bibFSZ1008709
terminal_url | https://webpac.lib.unideb.hu/WebPac/CorvinaWeb?action=cclfind&amp;resultview=long&amp;ccltext=idno+bibFSZ1008709

-[ RECORD 13 ]---------------------------------------------------------------------------------------------------------------------
oai_id       | oai:unsworks.library.unsw.edu.au:1959.4/64871
base_url     | http://handle.unsw.edu.au/1959.4/64871
terminal_url | https://www.unsworks.unsw.edu.au/primo-explore/fulldisplay?vid=UNSWORKS&docid=unsworks_62832&context=L

-[ RECORD 14 ]---------------------------------------------------------------------------------------------------------------------
oai_id       | oai:www.wbc.poznan.pl:225930
base_url     | https://www.wbc.poznan.pl/dlibra/docmetadata?showContent=true&id=225930
terminal_url | https://www.wbc.poznan.pl/dlibra/docmetadata?showContent=true&id=225930

SOFT-404

-[ RECORD 15 ]---------------------------------------------------------------------------------------------------------------------
oai_id       | oai:repository.erciyes.edu.tr:105
base_url     | http://repository.erciyes.edu.tr/bilimname/items/show/105
terminal_url | http://repository.erciyes.edu.tr:80/bilimname/items/show/105

GONE (domain not registered)

-[ RECORD 16 ]---------------------------------------------------------------------------------------------------------------------
oai_id       | oai:digi.ub.uni-heidelberg.de:37500
base_url     | https://archivum-laureshamense-digital.de/view/sad_a1_nr_20_13
terminal_url | https://archivum-laureshamense-digital.de/view/sad_a1_nr_20_13

Seems like a bespoke site

SKIP-BESPOKE

-[ RECORD 17 ]---------------------------------------------------------------------------------------------------------------------
oai_id       | oai:t2r2.star.titech.ac.jp:50401364
base_url     | http://t2r2.star.titech.ac.jp/cgi-bin/publicationinfo.cgi?q_publication_content_number=CTT100758313
terminal_url | http://t2r2.star.titech.ac.jp/cgi-bin/publicationinfo.cgi?q_publication_content_number=CTT100758313

METADATA-ONLY

-[ RECORD 18 ]---------------------------------------------------------------------------------------------------------------------
oai_id       | oai:epubs.cclrc.ac.uk:work/4714
base_url     | http://purl.org/net/epubs/work/4714
terminal_url | https://epubs.stfc.ac.uk/work/4714

It's got a purl! haha.

METADATA-ONLY

------

Another batch! With some repeat domains removed.

-[ RECORD 1 ]+-----------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:cris.vtt.fi:persons/142c030f-ba7b-491a-8669-a361088355cc
base_url     | https://cris.vtt.fi/en/persons/142c030f-ba7b-491a-8669-a361088355cc
terminal_url | https://cris.vtt.fi/en/persons/oleg-antropov

SKIP

-[ RECORD 2 ]+-----------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:etd.adm.unipi.it:etd-05302014-183910
base_url     | http://etd.adm.unipi.it/theses/available/etd-05302014-183910/
terminal_url | https://etd.adm.unipi.it/theses/available/etd-05302014-183910/

Some software platform? Pretty basic/bespoke

FIXED-PARTIAL

-[ RECORD 3 ]+-----------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:bibliotecadigital.jcyl.es:10000098246
base_url     | http://bibliotecadigital.jcyl.es/i18n/catalogo_imagenes/grupo.cmd?path=10316451
terminal_url | http://bibliotecadigital.jcyl.es/i18n/catalogo_imagenes/grupo.cmd?path=10316451

SKIP (see elsewhere)

-[ RECORD 7 ]+-----------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:elektra.cdaea.es:documento.29259
base_url     | https://www.juntadeandalucia.es/cultura/cdaea/elektra/catalogo_execute.html?tipoObjeto=1&id=29259
terminal_url | https://www.juntadeandalucia.es/cultura/cdaea/elektra/catalogo_execute.html?tipoObjeto=1&id=29259

Photo.

SKIP-SCOPE

-[ RECORD 9 ]+-----------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:unsworks.library.unsw.edu.au:1959.4/unsworks_60829
base_url     | http://handle.unsw.edu.au/1959.4/unsworks_60829
terminal_url | https://www.unsworks.unsw.edu.au/primo-explore/fulldisplay?vid=UNSWORKS&docid=unsworks_modsunsworks_60829&context=L

METADATA-ONLY

-[ RECORD 12 ]-----------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:pure.leuphana.de:publications/7d040cf2-b3b5-4671-8906-76b5bc8d870a
base_url     | http://fox.leuphana.de/portal/de/publications/studies-in-childrens-literature-1500--2000-editors-celia-keenan-(7d040cf2-b3b5-4671-8906-76b5bc8d870a).html
terminal_url | http://fox.leuphana.de/portal/de/publications/studies-in-childrens-literature-1500--2000-editors-celia-keenan-(7d040cf2-b3b5-4671-8906-76b5bc8d870a).html

unsure

-[ RECORD 16 ]-----------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:library.wur.nl:wurpubs/369344
base_url     | https://library.wur.nl/WebQuery/wurpubs/369344
terminal_url | https://library.wur.nl/WebQuery/wurpubs/369344

this specific record not OA (but site is fine/fixed)

-[ RECORD 17 ]-----------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:escholarship.umassmed.edu:oapubs-2146
base_url     | https://escholarship.umassmed.edu/oapubs/1147
terminal_url | http://escholarship.umassmed.edu/oapubs/1147/

just links to publisher (no content in repo)

-[ RECORD 18 ]-----------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:digitalcommons.usu.edu:wild_facpub-1010
base_url     | https://digitalcommons.usu.edu/wild_facpub/11
terminal_url | http://digitalcommons.usu.edu/wild_facpub/11/

also just links to publisher (no content in repo)

-[ RECORD 25 ]-----------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:igi.indrastra.com:306768
base_url     | http://igi.indrastra.com/items/show/306768
terminal_url | http://igi.indrastra.com/items/show/306768

(see elsewhere)

-[ RECORD 26 ]-----------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:fau.digital.flvc.org:fau_9804
base_url     | http://purl.flvc.org/fcla/dt/12932
terminal_url | http://fau.digital.flvc.org/islandora/object/fau%3A9804

Islandora.

-[ RECORD 27 ]-----------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:dspace.lu.lv:7/16019
base_url     | https://dspace.lu.lv/dspace/handle/7/16019
terminal_url | https://dspace.lu.lv/dspace/handle/7/16019

LOGINWALL

-[ RECORD 28 ]-----------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:zir.nsk.hr:umas_218
base_url     | https://repozitorij.svkst.unist.hr/islandora/object/umas:218
terminal_url | https://repozitorij.svkst.unist.hr/islandora/object/umas:218

REMOVED


-[ RECORD 29 ]-----------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:digi.ub.uni-heidelberg.de:36390
base_url     | https://digi.hadw-bw.de/view/sbhadwmnkl_a_1917_5
terminal_url | https://digi.hadw-bw.de/view/sbhadwmnkl_a_1917_5

Book, with chapters, not an individual work.

-[ RECORD 2 ]+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:krm.or.kr:10056135m201r
base_url     | https://www.krm.or.kr/krmts/link.html?dbGubun=SD&m201_id=10056135&res=y
terminal_url | https://www.krm.or.kr/krmts/search/detailview/research.html?dbGubun=SD&category=Research&m201_id=10056135

research results repository; keep crawling

SKIP-SCOPE

-[ RECORD 3 ]+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:www.db-thueringen.de:dbt_mods_00005191
base_url     | https://www.db-thueringen.de/receive/dbt_mods_00005191
terminal_url | https://www.db-thueringen.de/receive/dbt_mods_00005191

powered by "MyCoRe"

FIXED-MYCORE

-[ RECORD 6 ]+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:bibliotecavirtualandalucia.juntadeandalucia.es:1017405
base_url     | http://www.bibliotecavirtualdeandalucia.es/catalogo/es/consulta/registro.cmd?id=1017405
terminal_url | http://www.bibliotecavirtualdeandalucia.es/catalogo/es/consulta/registro.cmd?id=1017405

seems to be a general purpose regional library? not research-specific

SKIP-UNSURE

-[ RECORD 7 ]+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:etd.adm.unipi.it:etd-02272019-123644
base_url     | http://etd.adm.unipi.it/theses/available/etd-02272019-123644/
terminal_url | https://etd.adm.unipi.it/theses/available/etd-02272019-123644/

This specific URL is not available (FORBIDDEN)

others have multiple files, not just a single PDF:
https://etd.adm.unipi.it/t/etd-09102013-124430/

SKIP-UNSURE

-[ RECORD 9 ]+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:commons.ln.edu.hk:sw_master-5408
base_url     | https://commons.ln.edu.hk/sw_master/4408
terminal_url | https://commons.ln.edu.hk/sw_master/4408/

worth crawling I guess

METADATA-ONLY

-[ RECORD 10 ]------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:mouseion.jax.org:ssbb1976-1224
base_url     | https://mouseion.jax.org/ssbb1976/225
terminal_url | https://mouseion.jax.org/ssbb1976/225/

METADATA-ONLY

-[ RECORD 13 ]------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:aleph.bib-bvb.de:bvb01-016604343
base_url     | http://bvbm1.bib-bvb.de/webclient/DeliveryManager?pid=176332&custom_att_2=simple_viewer
terminal_url | http://digital.bib-bvb.de/view/action/singleViewer.do?dvs=1593269021002~476&locale=en_US&VIEWER_URL=/view/action/singleViewer.do?&DELIVERY_RULE_ID=31&frameId=1&usePid1=true&usePid2=true

SOFT-404 / FORBIDDEN (cookie timeout)

-[ RECORD 14 ]------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:bivaldi.gva.es:11740
base_url     | https://bivaldi.gva.es/es/consulta/registro.do?id=11740
terminal_url | https://bivaldi.gva.es/es/consulta/registro.do?id=11740


-[ RECORD 16 ]------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:library.wur.nl:wurpubs/443282
base_url     | https://library.wur.nl/WebQuery/wurpubs/443282
terminal_url | https://library.wur.nl/WebQuery/wurpubs/443282

DIGIBIS platform (like some others)

FIXED-PARTIAL

-[ RECORD 18 ]------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:hal:in2p3-00414135v1
base_url     | http://hal.in2p3.fr/in2p3-00414135
terminal_url | http://hal.in2p3.fr:80/in2p3-00414135

METADATA-ONLY

-[ RECORD 19 ]------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:aaltodoc.aalto.fi:123456789/13201
base_url     | https://aaltodoc.aalto.fi/handle/123456789/13201
terminal_url | https://aaltodoc.aalto.fi/handle/123456789/13201

This specific record is not accessible.
Another: https://aaltodoc.aalto.fi/handle/123456789/38002

DSpace 5.4

Worked (from recent changes)


-[ RECORD 20 ]------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
oai_id       | oai:sedici.unlp.edu.ar:10915/40144
base_url     | http://xjornadaslc.fahce.unlp.edu.ar/actas/Ramon_Esteban_Chaparro.pdf/view
terminal_url | http://xjornadaslc.fahce.unlp.edu.ar/actas/Ramon_Esteban_Chaparro.pdf/view

This is a journal! Cool. Plone software platform.

FIXED

## Top no-capture Domains

Top terminal no-capture domains:

    SELECT domain, COUNT(domain)
    FROM (
        SELECT
            ingest_file_result.ingest_type,
            ingest_file_result.status,
            substring(ingest_file_result.terminal_url FROM '[^/]+://([^/]*)') AS domain
        FROM ingest_file_result
        LEFT JOIN ingest_request
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'oai'
            AND ingest_file_result.status = 'no-capture'
    ) t1
    WHERE t1.domain != ''
        AND t1.status != 'success'
    GROUP BY domain
    ORDER BY COUNT DESC
    LIMIT 30;

                  domain               | count 
    -----------------------------------+-------
     digitalrepository.unm.edu         | 94087
     escholarship.org                  | 80632
     ir.opt.ac.cn                      | 70504
     idus.us.es                        | 67908
     www.cambridge.org                 | 56376
     www.ssoar.info                    | 52534
     rep.bntu.by                       | 52127
     scholarworks.umt.edu              | 48546
     publikationen.ub.uni-frankfurt.de | 46987
     dk.um.si                          | 45753
     repositorio.uladech.edu.pe        | 37028
     uu.diva-portal.org                | 34929
     digitalcommons.law.byu.edu        | 31732
     sedici.unlp.edu.ar                | 31233
     elib.sfu-kras.ru                  | 29131
     jyx.jyu.fi                        | 28144
     www.repository.cam.ac.uk          | 27728
     nagoya.repo.nii.ac.jp             | 26673
     www.duo.uio.no                    | 25258
     www.persee.fr                     | 24968
     www2.senado.leg.br                | 24426
     tesis.ucsm.edu.pe                 | 24049
     digitalcommons.unl.edu            | 21974
     www.degruyter.com                 | 21940
     www.igi-global.com                | 20736
     thekeep.eiu.edu                   | 20712
     docs.lib.purdue.edu               | 20538
     repositorio.cepal.org             | 20280
     elib.bsu.by                       | 19620
     minds.wisconsin.edu               | 19473
    (30 rows)

These all seem worth crawling. A couple publishers (cambridge.org), and
persee.fr will probably fail, but not too many URLs.

## Summary of Filtered Prefixes and Domains (OAI-PMH)

oai:kb.dk:
    too large and generic
oai:bdr.oai.bsb-muenchen.de:
    too large and generic
oai:hispana.mcu.es:
    too large and generic
oai:bnf.fr:
    too large and generic
oai:ukm.si:
    too large and generic
oai:biodiversitylibrary.org:
    redundant with other ingest and archive.org content
oai:hsp.org:
    large; historical content only
oai:repec:
    large; mostly (entirely?) links to publisher sites
oai:n/a:
    meta?
oai:quod.lib.umich.edu:
    entire issues? hard to crawl so skip for now
oai:hypotheses.org:
    HTML, not PDF
oai:americanae.aecid.es:
    large, complex. skip for now
oai:www.irgrid.ac.cn:
    aggregator of other IRs
oai:espace.library.uq.edu.au:
    large; metadata only; javascript heavy (poor heritrix crawling)
oai:edoc.mpg.de:
    deprecated domain, with no redirects
oai:bibliotecadigital.jcyl.es:
    digitized historical docs; hard to crawl, skip for now
oai:repository.erciyes.edu.tr:
    gone (domain lapsed)
oai:krm.or.kr:
    "research results repository" (metadata only)

www.kb.dk
    large, general purpose, scope
kb-images.kb.dk
    deprecated
mdz-nbn-resolving.de
    multiple prefixes end up here. historical docs, scope
aggr.ukm.um.si
    large, out of scope
edoc.mpg.de
    deprecated domain
doaj.org
    index (metadata only)
orcid.org
    out of scope
gateway.isiknowledge.com
    clarivate login/payall (skipping in ingest)

Needs filtering to a subset of records (by 'set' or other filtering?):

oai:igi.indrastra.com:
oai:invenio.nusl.cz:
oai:t2r2.star.titech.ac.jp:
oai:evastar-karlsruhe.de:
oai:repository.ust.hk:
oai:serval.unil.ch:
oai:pure.atira.dk:

FIlters in SQL syntax:

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

and in some contexts (PDFs; switch to HTML):

    AND ingest_request.link_source_id NOT LIKE 'oai:hypotheses.org:%'

## Overall Summary of OAI-PMH Stuff

Big picture is that the majority of `no-pdf-link` crawl status are because of
repository scope, record scope, or content format issues. That being said,
there was a sizable fraction of sites which were platforms (like DSpace) which
were not ingesting well.

A significant fraction of records are "metadata only" (of papers), or non-paper
entity types (like persons, grants, or journal titles), and a growing fraction
(?) are metadata plus link to OA publisher fulltext (offsite). Might be
possible to detect these at ingest time, or earlier at OAI-PMH
harvest/transform time and filter them out.

It may be worthwhile to attempt ingest of multiple existing captures
(timestamps) in the ingest pipeline.  Eg, instead of chosing a single "best"
capture, if there are multiple HTTP 200 status captures, try ingest with each
(or at least a couple).  This is because repository software gets upgraded, so
old "no-capture" or "not found" or "link loop" type captures may work when
recrawled.

New summary with additional filters:

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

            status         |  count
    -----------------------+----------
     success               | 12872279
     no-pdf-link           |  9329602
     no-capture            |  4696362
     redirect-loop         |  1541458
     terminal-bad-status   |   660418
     link-loop             |   452831
     wrong-mimetype        |   434868
     null-body             |    71065
     cdx-error             |    17005
                           |    15275
     petabox-error         |    12743
     wayback-error         |    11759
     skip-url-blocklist    |      182
     gateway-timeout       |      122
     redirects-exceeded    |      120
     bad-redirect          |      117
     bad-gzip-encoding     |      111
     wayback-content-error |      102
     timeout               |       72
     blocked-cookie        |       62
    (20 rows)

