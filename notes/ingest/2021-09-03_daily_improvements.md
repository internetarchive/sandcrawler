
Periodic check-in of daily crawling/ingest.

Overall ingest status, past 30 days:

    SELECT ingest_file_result.ingest_type, ingest_file_result.status, COUNT(*)
    FROM ingest_file_result
    LEFT JOIN ingest_request
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE ingest_request.created >= NOW() - '30 day'::INTERVAL
        AND ingest_request.ingest_type = 'pdf'
        AND ingest_request.ingest_request_source = 'fatcat-changelog'
    GROUP BY ingest_file_result.ingest_type, ingest_file_result.status
    ORDER BY COUNT DESC
    LIMIT 20;

     ingest_type |         status          | count  
    -------------+-------------------------+--------
     pdf         | no-pdf-link             | 158474
     pdf         | spn2-cdx-lookup-failure | 135344
     pdf         | success                 | 127938
     pdf         | spn2-error              |  65411
     pdf         | gateway-timeout         |  63112
     pdf         | blocked-cookie          |  26338
     pdf         | terminal-bad-status     |  24853
     pdf         | link-loop               |  15699
     pdf         | spn2-error:job-failed   |  13862
     pdf         | redirect-loop           |  11432
     pdf         | cdx-error               |   2376
     pdf         | too-many-redirects      |   2186
     pdf         | wrong-mimetype          |   2142
     pdf         | forbidden               |   1758
     pdf         | spn2-error:no-status    |    972
     pdf         | not-found               |    820
     pdf         | bad-redirect            |    536
     pdf         | read-timeout            |    392
     pdf         | wayback-error           |    251
     pdf         | remote-server-error     |    220
    (20 rows)

Hrm, that is a healthy fraction of `no-pdf-link`.

Broken domains, past 30 days:

    SELECT domain, status, COUNT((domain, status))
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
            -- ingest_request.created >= NOW() - '3 day'::INTERVAL
            ingest_file_result.updated >= NOW() - '30 day'::INTERVAL
            AND ingest_request.ingest_type = 'pdf'
            AND ingest_request.ingest_request_source = 'fatcat-changelog'
    ) t1
    WHERE t1.domain != ''
        AND t1.status != 'success'
    GROUP BY domain, status
    ORDER BY COUNT DESC
    LIMIT 25;

             domain          |         status          | count
    -------------------------+-------------------------+-------
     zenodo.org              | no-pdf-link             | 39678
     osf.io                  | gateway-timeout         | 29809
     acervus.unicamp.br      | no-pdf-link             | 21978
     osf.io                  | terminal-bad-status     | 18727
     zenodo.org              | spn2-cdx-lookup-failure | 17008
     doi.org                 | spn2-cdx-lookup-failure | 15503
     www.degruyter.com       | no-pdf-link             | 15122
     ieeexplore.ieee.org     | spn2-error:job-failed   | 12921
     osf.io                  | spn2-cdx-lookup-failure | 11123
     www.tandfonline.com     | blocked-cookie          |  8096
     www.morressier.com      | no-pdf-link             |  4655
     ieeexplore.ieee.org     | spn2-cdx-lookup-failure |  4580
     pubs.acs.org            | blocked-cookie          |  4415
     www.frontiersin.org     | no-pdf-link             |  4163
     www.degruyter.com       | spn2-cdx-lookup-failure |  3788
     www.taylorfrancis.com   | no-pdf-link             |  3568
     www.sciencedirect.com   | no-pdf-link             |  3128
     www.taylorfrancis.com   | spn2-cdx-lookup-failure |  3116
     acervus.unicamp.br      | spn2-cdx-lookup-failure |  2797
     www.mdpi.com            | spn2-cdx-lookup-failure |  2719
     brill.com               | link-loop               |  2681
     linkinghub.elsevier.com | spn2-cdx-lookup-failure |  2657
     www.sciencedirect.com   | spn2-cdx-lookup-failure |  2546
     apps.crossref.org       | no-pdf-link             |  2537
     onlinelibrary.wiley.com | blocked-cookie          |  2528
    (25 rows)

Summary of significant domains and status, past 30 days, minus spn2-cdx-lookup-failure:

    SELECT domain, status, count
    FROM (
        SELECT domain, status, COUNT((domain, status)) as count
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
                ingest_file_result.updated >= NOW() - '30 day'::INTERVAL
                AND ingest_request.ingest_type = 'pdf'
                AND ingest_request.ingest_request_source = 'fatcat-changelog'
                AND ingest_file_result.status != 'spn2-cdx-lookup-failure'
        ) t1
        WHERE t1.domain != ''
        GROUP BY CUBE (domain, status)
    ) t2
    WHERE count > 200
    ORDER BY domain ASC , count DESC;


                                domain                              |        status         | count  
    -----------------------------------------------------------------+-----------------------+--------
    academic.oup.com                                                |                       |   2405
    academic.oup.com                                                | no-pdf-link           |   1240
    academic.oup.com                                                | link-loop             |   1010
    acervus.unicamp.br                                              |                       |  21980
    acervus.unicamp.br                                              | no-pdf-link           |  21978 **
    aclanthology.org                                                |                       |    208
    acp.copernicus.org                                              |                       |    365
    acp.copernicus.org                                              | success               |    356
    aip.scitation.org                                               |                       |   1071
    aip.scitation.org                                               | blocked-cookie        |    843
    aip.scitation.org                                               | redirect-loop         |    227
    apps.crossref.org                                               |                       |   2537
    apps.crossref.org                                               | no-pdf-link           |   2537
    arxiv.org                                                       |                       |  17817
    arxiv.org                                                       | success               |  17370
    arxiv.org                                                       | terminal-bad-status   |    320
    asmedigitalcollection.asme.org                                  |                       |    401
    asmedigitalcollection.asme.org                                  | link-loop             |    364
    assets.researchsquare.com                                       |                       |   3706
    assets.researchsquare.com                                       | success               |   3706
    avmj.journals.ekb.eg                                            |                       |    605
    avmj.journals.ekb.eg                                            | success               |    595
    bfa.journals.ekb.eg                                             |                       |    224
    bfa.journals.ekb.eg                                             | success               |    214
    biorxiv.org                                                     | redirect-loop         |    895
    biorxiv.org                                                     |                       |    895
    birdsoftheworld.org                                             |                       |    286
    birdsoftheworld.org                                             | no-pdf-link           |    285
    bmjopen.bmj.com                                                 | success               |    232
    bmjopen.bmj.com                                                 |                       |    232
    books.openedition.org                                           |                       |    396
    books.openedition.org                                           | no-pdf-link           |    396
    brill.com                                                       |                       |   4272
    brill.com                                                       | link-loop             |   2681
    brill.com                                                       | no-pdf-link           |   1410
    cas.columbia.edu                                                |                       |   1038
    cas.columbia.edu                                                | no-pdf-link           |   1038 **
    cdr.lib.unc.edu                                                 |                       |    513
    cdr.lib.unc.edu                                                 | success               |    469
    chemrxiv.org                                                    |                       |    278
    chemrxiv.org                                                    | success               |    275
    classiques-garnier.com                                          |                       |    531
    classiques-garnier.com                                          | no-pdf-link           |    487 *
    content.iospress.com                                            |                       |    275
    content.iospress.com                                            | link-loop             |    230
    cris.maastrichtuniversity.nl                                    |                       |    318
    cris.maastrichtuniversity.nl                                    | success               |    284
    cyberleninka.ru                                                 |                       |   1165
    cyberleninka.ru                                                 | success               |   1134
    deepblue.lib.umich.edu                                          |                       |    289
    dergipark.org.tr                                                |                       |   1185
    dergipark.org.tr                                                | success               |    774
    dergipark.org.tr                                                | no-pdf-link           |    320
    didaktorika.gr                                                  |                       |    688
    didaktorika.gr                                                  | redirect-loop         |    688
    digi.ub.uni-heidelberg.de                                       |                       |    292
    digi.ub.uni-heidelberg.de                                       | no-pdf-link           |    292
    direct.mit.edu                                                  |                       |    236
    direct.mit.edu                                                  | no-pdf-link           |    207 *
    dl.acm.org                                                      |                       |   2319
    dl.acm.org                                                      | blocked-cookie        |   2230
    dmtcs.episciences.org                                           |                       |    733
    dmtcs.episciences.org                                           | success               |    730
    doi.ala.org.au                                                  | no-pdf-link           |   2373 **
    doi.ala.org.au                                                  |                       |   2373
    doi.org                                                         |                       |    732
    doi.org                                                         | terminal-bad-status   |    673
    downloads.hindawi.com                                           | success               |   1452
    downloads.hindawi.com                                           |                       |   1452
    drive.google.com                                                |                       |    216
    drive.google.com                                                | no-pdf-link           |    211
    dtb.bmj.com                                                     |                       |    674
    dtb.bmj.com                                                     | link-loop             |    669
    easy.dans.knaw.nl                                               | no-pdf-link           |    261 *
    easy.dans.knaw.nl                                               |                       |    261
    ebooks.marilia.unesp.br                                         |                       |    688
    ebooks.marilia.unesp.br                                         | no-pdf-link           |    688 *
    ehp.niehs.nih.gov                                               |                       |    766
    ehp.niehs.nih.gov                                               | blocked-cookie        |    765
    ejournal.mandalanursa.org                                       |                       |    307
    ejournal.mandalanursa.org                                       | success               |    305
    elib.spbstu.ru                                                  |                       |    264
    elib.spbstu.ru                                                  | redirect-loop         |    257
    elibrary.ru                                                     |                       |   1367
    elibrary.ru                                                     | redirect-loop         |   1169
    elibrary.vdi-verlag.de                                          |                       |   1251
    elibrary.vdi-verlag.de                                          | no-pdf-link           |    646
    elibrary.vdi-verlag.de                                          | link-loop             |    537
    elifesciences.org                                               |                       |    328
    elifesciences.org                                               | success               |    323
    figshare.com                                                    |                       |    803
    figshare.com                                                    | no-pdf-link           |    714 *
    files.osf.io                                                    |                       |    745
    files.osf.io                                                    | success               |    614
    hammer.purdue.edu                                               |                       |    244
    hammer.purdue.edu                                               | no-pdf-link           |    243
    heiup.uni-heidelberg.de                                         |                       |    277
    heiup.uni-heidelberg.de                                         | no-pdf-link           |    268
    hkvalidate.perfdrive.com                                        | no-pdf-link           |    370 *
    hkvalidate.perfdrive.com                                        |                       |    370
    ieeexplore.ieee.org                                             |                       |  16675
    ieeexplore.ieee.org                                             | spn2-error:job-failed |  12927
    ieeexplore.ieee.org                                             | success               |   1952
    ieeexplore.ieee.org                                             | too-many-redirects    |   1193
    ieeexplore.ieee.org                                             | no-pdf-link           |    419
    jamanetwork.com                                                 |                       |    339
    jamanetwork.com                                                 | success               |    216
    jmstt.ntou.edu.tw                                               |                       |    244
    jmstt.ntou.edu.tw                                               | success               |    241
    journal.ipb.ac.id                                               |                       |    229
    journal.ipb.ac.id                                               | success               |    206
    journal.nafe.org                                                |                       |    221
    journals.aps.org                                                |                       |    614
    journals.aps.org                                                | gateway-timeout       |    495
    journals.asm.org                                                |                       |    463
    journals.asm.org                                                | blocked-cookie        |    435
    journals.flvc.org                                               |                       |    230
    journals.lww.com                                                |                       |   1300
    journals.lww.com                                                | link-loop             |   1284
    journals.openedition.org                                        |                       |    543
    journals.openedition.org                                        | success               |    311
    journals.ub.uni-heidelberg.de                                   |                       |    357
    journals.ub.uni-heidelberg.de                                   | success               |    311
    jov.arvojournals.org                                            |                       |    431
    jov.arvojournals.org                                            | no-pdf-link           |    422 *
    kiss.kstudy.com                                                 |                       |    303
    kiss.kstudy.com                                                 | no-pdf-link           |    303 *
    library.iated.org                                               |                       |    364
    library.iated.org                                               | redirect-loop         |    264
    library.seg.org                                                 | blocked-cookie        |    301
    library.seg.org                                                 |                       |    301
    link.aps.org                                                    | redirect-loop         |    442
    link.aps.org                                                    |                       |    442
    linkinghub.elsevier.com                                         |                       |    515
    linkinghub.elsevier.com                                         | gateway-timeout       |    392
    mc.sbm.org.br                                                   |                       |    224
    mc.sbm.org.br                                                   | success               |    224
    mdpi-res.com                                                    |                       |    742
    mdpi-res.com                                                    | success               |    742
    mdsoar.org                                                      |                       |    220
    mediarep.org                                                    |                       |    269
    mediarep.org                                                    | success               |    264
    medrxiv.org                                                     | redirect-loop         |    290
    medrxiv.org                                                     |                       |    290
    muse.jhu.edu                                                    |                       |    429
    muse.jhu.edu                                                    | terminal-bad-status   |    391
    mvmj.journals.ekb.eg                                            |                       |    306
    oapub.org                                                       |                       |    292
    oapub.org                                                       | success               |    289
    onepetro.org                                                    |                       |    426
    onepetro.org                                                    | link-loop             |    406
    onlinelibrary.wiley.com                                         |                       |   2835
    onlinelibrary.wiley.com                                         | blocked-cookie        |   2531
    onlinelibrary.wiley.com                                         | redirect-loop         |    264
    open.library.ubc.ca                                             |                       |    569
    open.library.ubc.ca                                             | no-pdf-link           |    425 *
    opendata.uni-halle.de                                           |                       |    407
    opendata.uni-halle.de                                           | success               |    263
    osf.io                                                          |                       |  49022
    osf.io                                                          | gateway-timeout       |  29810
    osf.io                                                          | terminal-bad-status   |  18731
    osf.io                                                          | spn2-error            |    247
    osf.io                                                          | not-found             |    205
    oxford.universitypressscholarship.com                           |                       |    392
    oxford.universitypressscholarship.com                           | link-loop             |    233
    panor.ru                                                        | no-pdf-link           |    433 *
    panor.ru                                                        |                       |    433
    papers.ssrn.com                                                 |                       |   1630
    papers.ssrn.com                                                 | link-loop             |   1598
    pdf.sciencedirectassets.com                                     |                       |   3063
    pdf.sciencedirectassets.com                                     | success               |   3063
    peerj.com                                                       |                       |    464
    peerj.com                                                       | no-pdf-link           |    303 *
    periodicos.ufpe.br                                              |                       |    245
    periodicos.ufpe.br                                              | success               |    232
    periodicos.unb.br                                               |                       |    230
    periodicos.unb.br                                               | success               |    221
    preprints.jmir.org                                              |                       |    548
    preprints.jmir.org                                              | cdx-error             |    499
    publications.rwth-aachen.de                                     |                       |    213
    publikationen.bibliothek.kit.edu                                |                       |    346
    publikationen.bibliothek.kit.edu                                | success               |    314
    publikationen.uni-tuebingen.de                                  |                       |    623
    publikationen.uni-tuebingen.de                                  | no-pdf-link           |    522 *
    publons.com                                                     | no-pdf-link           |    934 *
    publons.com                                                     |                       |    934
    pubs.acs.org                                                    |                       |   4507
    pubs.acs.org                                                    | blocked-cookie        |   4406
    pubs.rsc.org                                                    |                       |   1638
    pubs.rsc.org                                                    | link-loop             |   1054
    pubs.rsc.org                                                    | redirect-loop         |    343
    pubs.rsc.org                                                    | success               |    201
    repositorio.ufu.br                                              |                       |    637
    repositorio.ufu.br                                              | success               |    607
    repository.dri.ie                                               |                       |   1852
    repository.dri.ie                                               | no-pdf-link           |   1852 **
    repository.library.brown.edu                                    |                       |    293
    repository.library.brown.edu                                    | no-pdf-link           |    291 *
    res.mdpi.com                                                    |                       |  10367
    res.mdpi.com                                                    | success               |  10360
    retrovirology.biomedcentral.com                                 |                       |    230
    revistas.ufrj.br                                                |                       |    284
    revistas.ufrj.br                                                | success               |    283
    revistas.uptc.edu.co                                            |                       |    385
    revistas.uptc.edu.co                                            | success               |    344
    royalsocietypublishing.org                                      |                       |    231
    rsdjournal.org                                                  |                       |    347
    rsdjournal.org                                                  | success               |    343
    s3-ap-southeast-2.amazonaws.com                                 |                       |    400
    s3-ap-southeast-2.amazonaws.com                                 | success               |    392
    s3-eu-west-1.amazonaws.com                                      |                       |   2096
    s3-eu-west-1.amazonaws.com                                      | success               |   2091
    s3-euw1-ap-pe-df-pch-content-store-p.s3.eu-west-1.amazonaws.com |                       |    289
    s3-euw1-ap-pe-df-pch-content-store-p.s3.eu-west-1.amazonaws.com | success               |    286
    s3.ca-central-1.amazonaws.com                                   |                       |    202
    sage.figshare.com                                               |                       |    242
    sage.figshare.com                                               | no-pdf-link           |    241
    sajeb.org                                                       |                       |    246
    sajeb.org                                                       | no-pdf-link           |    243
    scholar.dkyobobook.co.kr                                        |                       |    332
    scholar.dkyobobook.co.kr                                        | no-pdf-link           |    328 *
    search.mandumah.com                                             |                       |    735
    search.mandumah.com                                             | redirect-loop         |    726
    secure.jbs.elsevierhealth.com                                   |                       |   1112
    secure.jbs.elsevierhealth.com                                   | blocked-cookie        |   1108
    stm.bookpi.org                                                  | no-pdf-link           |    468 *
    stm.bookpi.org                                                  |                       |    468
    storage.googleapis.com                                          |                       |   1012
    storage.googleapis.com                                          | success               |   1012
    tandf.figshare.com                                              |                       |    469
    tandf.figshare.com                                              | no-pdf-link           |    466
    teses.usp.br                                                    |                       |    739
    teses.usp.br                                                    | success               |    730
    tidsskrift.dk                                                   |                       |    360
    tidsskrift.dk                                                   | success               |    346
    tiedejaedistys.journal.fi                                       |                       |    224
    tind-customer-agecon.s3.amazonaws.com                           | success               |    332
    tind-customer-agecon.s3.amazonaws.com                           |                       |    332
    valep.vc.univie.ac.at                                           | no-pdf-link           |    280
    valep.vc.univie.ac.at                                           |                       |    280
    watermark.silverchair.com                                       |                       |   1729
    watermark.silverchair.com                                       | success               |   1719
    www.academia.edu                                                |                       |    387
    www.academia.edu                                                | no-pdf-link           |    386
    www.ahajournals.org                                             |                       |    430
    www.ahajournals.org                                             | blocked-cookie        |    413
    www.atenaeditora.com.br                                         |                       |    572
    www.atenaeditora.com.br                                         | terminal-bad-status   |    513
    www.atlantis-press.com                                          | success               |    722
    www.atlantis-press.com                                          |                       |    722
    www.aup-online.com                                              |                       |    419
    www.aup-online.com                                              | no-pdf-link           |    419 *
    www.beck-elibrary.de                                            |                       |    269
    www.beck-elibrary.de                                            | no-pdf-link           |    268 *
    www.biodiversitylibrary.org                                     | no-pdf-link           |    528 *
    www.biodiversitylibrary.org                                     |                       |    528
    www.bloomsburycollections.com                                   |                       |    623
    www.bloomsburycollections.com                                   | no-pdf-link           |    605 *
    www.cabi.org                                                    |                       |   2191
    www.cabi.org                                                    | no-pdf-link           |   2186 *
    www.cairn.info                                                  |                       |   1283
    www.cairn.info                                                  | no-pdf-link           |    713
    www.cairn.info                                                  | link-loop             |    345
    www.cambridge.org                                               |                       |   4128
    www.cambridge.org                                               | no-pdf-link           |   1531
    www.cambridge.org                                               | success               |   1441
    www.cambridge.org                                               | link-loop             |    971
    www.cureus.com                                                  | no-pdf-link           |    526 *
    www.cureus.com                                                  |                       |    526
    www.dbpia.co.kr                                                 |                       |    637
    www.dbpia.co.kr                                                 | redirect-loop         |    631
    www.deboni.he.com.br                                            |                       |    382
    www.deboni.he.com.br                                            | success               |    381
    www.degruyter.com                                               |                       |  17783
    www.degruyter.com                                               | no-pdf-link           |  15102
    www.degruyter.com                                               | success               |   2584
    www.dovepress.com                                               |                       |    480
    www.dovepress.com                                               | success               |    472
    www.e-manuscripta.ch                                            |                       |   1350
    www.e-manuscripta.ch                                            | no-pdf-link           |   1350 *
    www.e-periodica.ch                                              |                       |   1276
    www.e-periodica.ch                                              | no-pdf-link           |   1275
    www.e-rara.ch                                                   |                       |    202
    www.e-rara.ch                                                   | no-pdf-link           |    202
    www.elgaronline.com                                             |                       |    495
    www.elgaronline.com                                             | link-loop             |    290
    www.elibrary.ru                                                 |                       |    922
    www.elibrary.ru                                                 | no-pdf-link           |    904
    www.emerald.com                                                 |                       |   2155
    www.emerald.com                                                 | no-pdf-link           |   1936 *
    www.emerald.com                                                 | success               |    219
    www.eurekaselect.com                                            |                       |    518
    www.eurekaselect.com                                            | no-pdf-link           |    516 *
    www.frontiersin.org                                             |                       |   4163
    www.frontiersin.org                                             | no-pdf-link           |   4162 **
    www.hanser-elibrary.com                                         |                       |    444
    www.hanser-elibrary.com                                         | blocked-cookie        |    444
    www.hanspub.org                                                 |                       |    334
    www.hanspub.org                                                 | no-pdf-link           |    314
    www.idunn.no                                                    |                       |   1736
    www.idunn.no                                                    | link-loop             |    596
    www.idunn.no                                                    | success               |    577
    www.idunn.no                                                    | no-pdf-link           |    539
    www.igi-global.com                                              | terminal-bad-status   |    458
    www.igi-global.com                                              |                       |    458
    www.ijcai.org                                                   |                       |    533
    www.ijcai.org                                                   | success               |    532
    www.ijraset.com                                                 | success               |    385
    www.ijraset.com                                                 |                       |    385
    www.inderscience.com                                            |                       |    712
    www.inderscience.com                                            | no-pdf-link           |    605 *
    www.ingentaconnect.com                                          |                       |    456
    www.ingentaconnect.com                                          | no-pdf-link           |    413 *
    www.internationaljournalssrg.org                                |                       |    305
    www.internationaljournalssrg.org                                | no-pdf-link           |    305 *
    www.isca-speech.org                                             |                       |   2392
    www.isca-speech.org                                             | no-pdf-link           |   2391 **
    www.journals.uchicago.edu                                       |                       |    228
    www.journals.uchicago.edu                                       | blocked-cookie        |    227
    www.jstage.jst.go.jp                                            |                       |   1492
    www.jstage.jst.go.jp                                            | success               |   1185
    www.jstage.jst.go.jp                                            | no-pdf-link           |    289
    www.jstor.org                                                   |                       |    301
    www.jurology.com                                                |                       |    887
    www.jurology.com                                                | redirect-loop         |    887
    www.karger.com                                                  |                       |    318
    www.liebertpub.com                                              |                       |    507
    www.liebertpub.com                                              | blocked-cookie        |    496
    www.morressier.com                                              |                       |   4781
    www.morressier.com                                              | no-pdf-link           |   4655 **
    www.ncl.ecu.edu                                                 |                       |    413
    www.ncl.ecu.edu                                                 | success               |    413
    www.nomos-elibrary.de                                           |                       |    526
    www.nomos-elibrary.de                                           | no-pdf-link           |    391
    www.oecd-ilibrary.org                                           | no-pdf-link           |   1170 **
    www.oecd-ilibrary.org                                           |                       |   1170
    www.openagrar.de                                                | no-pdf-link           |    221
    www.openagrar.de                                                |                       |    221
    www.osapublishing.org                                           |                       |    900
    www.osapublishing.org                                           | link-loop             |    615
    www.osapublishing.org                                           | no-pdf-link           |    269
    www.osti.gov                                                    |                       |    630
    www.osti.gov                                                    | link-loop             |    573
    www.oxfordlawtrove.com                                          | no-pdf-link           |    476 *
    www.oxfordlawtrove.com                                          |                       |    476
    www.pdcnet.org                                                  |                       |    298
    www.pdcnet.org                                                  | terminal-bad-status   |    262
    www.pedocs.de                                                   |                       |    203
    www.pnas.org                                                    |                       |    222
    www.preprints.org                                               |                       |    372
    www.preprints.org                                               | success               |    366
    www.repository.cam.ac.uk                                        |                       |    801
    www.repository.cam.ac.uk                                        | success               |    359
    www.repository.cam.ac.uk                                        | no-pdf-link           |    239
    www.research-collection.ethz.ch                                 |                       |    276
    www.research-collection.ethz.ch                                 | terminal-bad-status   |    274
    www.revistas.usp.br                                             |                       |    207
    www.revistas.usp.br                                             | success               |    204
    www.rina.org.uk                                                 | no-pdf-link           |   1009 **
    www.rina.org.uk                                                 |                       |   1009
    www.schweizerbart.de                                            | no-pdf-link           |    202
    www.schweizerbart.de                                            |                       |    202
    www.scielo.br                                                   |                       |    544
    www.scielo.br                                                   | redirect-loop         |    526
    www.sciencedirect.com                                           |                       |   3901
    www.sciencedirect.com                                           | no-pdf-link           |   3127 **
    www.sciencedirect.com                                           | link-loop             |    701
    www.sciendo.com                                                 |                       |    384
    www.sciendo.com                                                 | success               |    363
    www.sciengine.com                                               |                       |    225
    www.scirp.org                                                   |                       |    209
    www.spandidos-publications.com                                  |                       |    205
    www.tandfonline.com                                             |                       |   8925
    www.tandfonline.com                                             | blocked-cookie        |   8099
    www.tandfonline.com                                             | terminal-bad-status   |    477
    www.tandfonline.com                                             | redirect-loop         |    322
    www.taylorfrancis.com                                           |                       |   6119
    www.taylorfrancis.com                                           | no-pdf-link           |   3567
    www.taylorfrancis.com                                           | link-loop             |   2169
    www.taylorfrancis.com                                           | terminal-bad-status   |    353
    www.thieme-connect.de                                           |                       |   1047
    www.thieme-connect.de                                           | redirect-loop         |    472
    www.thieme-connect.de                                           | spn2-error:job-failed |    343
    www.tib.eu                                                      |                       |    206
    www.trp.org.in                                                  |                       |    311
    www.trp.org.in                                                  | success               |    311
    www.un-ilibrary.org                                             | no-pdf-link           |    597 *
    www.un-ilibrary.org                                             |                       |    597
    www.vr-elibrary.de                                              |                       |    775
    www.vr-elibrary.de                                              | blocked-cookie        |    774
    www.wjgnet.com                                                  |                       |    204
    www.wjgnet.com                                                  | no-pdf-link           |    204
    www.worldscientific.com                                         |                       |    974
    www.worldscientific.com                                         | blocked-cookie        |    971
    www.worldwidejournals.com                                       |                       |    242
    www.worldwidejournals.com                                       | no-pdf-link           |    203
    www.wto-ilibrary.org                                            | no-pdf-link           |    295
    www.wto-ilibrary.org                                            |                       |    295
    www.zora.uzh.ch                                                 |                       |    222
    zenodo.org                                                      |                       |  49460
    zenodo.org                                                      | no-pdf-link           |  39721
    zenodo.org                                                      | success               |   8954
    zenodo.org                                                      | wrong-mimetype        |    562
                                                                    |                       | 445919
                                                                    | no-pdf-link           | 168035
                                                                    | success               | 140875
                                                                    | gateway-timeout       |  31809
                                                                    | blocked-cookie        |  26431
                                                                    | terminal-bad-status   |  25625
                                                                    | link-loop             |  19006
                                                                    | spn2-error:job-failed |  13962
                                                                    | redirect-loop         |  12512
                                                                    | wrong-mimetype        |   2302
                                                                    | spn2-error            |   1689
                                                                    | too-many-redirects    |   1203
                                                                    | bad-redirect          |    732
                                                                    | cdx-error             |    539
                                                                    | not-found             |    420
                                                                    | spn2-error:no-status  |    256
    (419 rows)

Get random subsets by terminal domain:

    \x auto
    SELECT
        ingest_request.link_source_id AS link_source_id,
        ingest_request.base_url as base_url ,
        ingest_file_result.terminal_url as terminal_url 
    FROM ingest_request
    LEFT JOIN ingest_file_result
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE
        ingest_request.created >= NOW() - '30 day'::INTERVAL
        AND ingest_request.ingest_type = 'pdf'
        AND ingest_request.ingest_request_source = 'fatcat-changelog'
        AND ingest_file_result.status = 'no-pdf-link'
        AND ingest_file_result.terminal_url LIKE '%//DOMAIN/%'
    ORDER BY random()
    LIMIT 5;

## acervus.unicamp.br

Previously flagged as messy (2021-05_daily_improvements.md)

## cas.columbia.edu

-[ RECORD 1 ]--+------------------------------------------------------------------------------------------------------------------
link_source_id | 10.7916/d8-2ety-qm51
base_url       | https://doi.org/10.7916/d8-2ety-qm51
terminal_url   | https://cas.columbia.edu/cas/login?TARGET=https%3A%2F%2Fdlc.library.columbia.edu%2Fusers%2Fauth%2Fsaml%2Fcallback
-[ RECORD 2 ]--+------------------------------------------------------------------------------------------------------------------
link_source_id | 10.7916/d8-0zf6-d167
base_url       | https://doi.org/10.7916/d8-0zf6-d167
terminal_url   | https://cas.columbia.edu/cas/login?TARGET=https%3A%2F%2Fdlc.library.columbia.edu%2Fusers%2Fauth%2Fsaml%2Fcallback
-[ RECORD 3 ]--+------------------------------------------------------------------------------------------------------------------
link_source_id | 10.7916/d8-k6ha-sn43
base_url       | https://doi.org/10.7916/d8-k6ha-sn43
terminal_url   | https://cas.columbia.edu/cas/login?TARGET=https%3A%2F%2Fdlc.library.columbia.edu%2Fusers%2Fauth%2Fsaml%2Fcallback
-[ RECORD 4 ]--+------------------------------------------------------------------------------------------------------------------
link_source_id | 10.7916/d8-bj6t-eb07
base_url       | https://doi.org/10.7916/d8-bj6t-eb07
terminal_url   | https://cas.columbia.edu/cas/login?TARGET=https%3A%2F%2Fdlc.library.columbia.edu%2Fusers%2Fauth%2Fsaml%2Fcallback
-[ RECORD 5 ]--+------------------------------------------------------------------------------------------------------------------
link_source_id | 10.7916/d8-xjac-j502
base_url       | https://doi.org/10.7916/d8-xjac-j502
terminal_url   | https://cas.columbia.edu/cas/login?TARGET=https%3A%2F%2Fdlc.library.columbia.edu%2Fusers%2Fauth%2Fsaml%2Fcallback

these are not public (loginwalls)

DONE: '/login?TARGET=' as a login wall pattern

## doi.ala.org.au

Previously flagged as dataset repository; datacite metadata is wrong. (2021-05_daily_improvements.md)

NOTE: look at ingesting datasets

## www.isca-speech.org

-[ RECORD 1 ]--+----------------------------------------------------------------------------------
link_source_id | 10.21437/interspeech.2014-84
base_url       | https://doi.org/10.21437/interspeech.2014-84
terminal_url   | https://www.isca-speech.org/archive/interspeech_2014/li14b_interspeech.html
-[ RECORD 2 ]--+----------------------------------------------------------------------------------
link_source_id | 10.21437/interspeech.2004-319
base_url       | https://doi.org/10.21437/interspeech.2004-319
terminal_url   | https://www.isca-speech.org/archive/interspeech_2004/delcroix04_interspeech.html
-[ RECORD 3 ]--+----------------------------------------------------------------------------------
link_source_id | 10.21437/interspeech.2006-372
base_url       | https://doi.org/10.21437/interspeech.2006-372
terminal_url   | https://www.isca-speech.org/archive/interspeech_2006/lei06c_interspeech.html
-[ RECORD 4 ]--+----------------------------------------------------------------------------------
link_source_id | 10.21437/interspeech.2015-588
base_url       | https://doi.org/10.21437/interspeech.2015-588
terminal_url   | https://www.isca-speech.org/archive/interspeech_2015/polzehl15b_interspeech.html
-[ RECORD 5 ]--+----------------------------------------------------------------------------------
link_source_id | 10.21437/interspeech.2006-468
base_url       | https://doi.org/10.21437/interspeech.2006-468
terminal_url   | https://www.isca-speech.org/archive/interspeech_2006/chitturi06b_interspeech.html

Bespoke site. Added rule to sandcrawler.

NOTE: re-ingest/recrawl all isca-speech.org no-pdf-link terminal URLs (fatcat-ingest?)

## www.morressier.com


-[ RECORD 1 ]--+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.1115/1.0002858v
base_url       | https://doi.org/10.1115/1.0002858v
terminal_url   | https://www.morressier.com/article/development-new-single-highdensity-heatflux-gauges-unsteady-heat-transfer-measurements-rotating-transonic-turbine/60f162805d86378f03b49af5
-[ RECORD 2 ]--+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.1115/1.0003896v
base_url       | https://doi.org/10.1115/1.0003896v
terminal_url   | https://www.morressier.com/article/experimental-investigation-proton-exchange-membrane-fuel-cell-platinum-nafion-along-inplane-direction/60f16d555d86378f03b50038
-[ RECORD 3 ]--+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.1115/1.0004476v
base_url       | https://doi.org/10.1115/1.0004476v
terminal_url   | https://www.morressier.com/article/effect-air-release-agents-performance-results-fabric-lined-bushings/60f16d585d86378f03b502d5
-[ RECORD 4 ]--+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.1115/1.0001286v
base_url       | https://doi.org/10.1115/1.0001286v
terminal_url   | https://www.morressier.com/article/development-verification-modelling-practice-cfd-calculations-obtain-current-loads-fpso/60f15d3fe537565438d70ece
-[ RECORD 5 ]--+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.1115/1.0000315v
base_url       | https://doi.org/10.1115/1.0000315v
terminal_url   | https://www.morressier.com/article/fire-event-analysis-fire-frequency-estimation-japanese-nuclear-power-plant/60f15a6f5d86378f03b43874

Many of these seem to be presentations, as both video and slides. PDFs seem broken though.

NOTE: add to list of interesting rich media to crawl/preserve (video+slides+data)

## www.oecd-ilibrary.org

Paywall (2021-05_daily_improvements.md)

## www.rina.org.uk

-[ RECORD 1 ]--+-------------------------------------------------------
link_source_id | 10.3940/rina.ws.2002.10
base_url       | https://doi.org/10.3940/rina.ws.2002.10
terminal_url   | https://www.rina.org.uk/showproducts.html?product=4116
-[ RECORD 2 ]--+-------------------------------------------------------
link_source_id | 10.3940/rina.pass.2003.16
base_url       | https://doi.org/10.3940/rina.pass.2003.16
terminal_url   | https://www.rina.org.uk/showproducts.html?product=3566
-[ RECORD 3 ]--+-------------------------------------------------------
link_source_id | 10.3940/rina.icsotin.2013.15
base_url       | https://doi.org/10.3940/rina.icsotin.2013.15
terminal_url   | https://www.rina.org.uk/showproducts.html?product=8017
-[ RECORD 4 ]--+-------------------------------------------------------
link_source_id | 10.3940/rina.wfa.2010.23
base_url       | https://doi.org/10.3940/rina.wfa.2010.23
terminal_url   | https://www.rina.org.uk/showproducts.html?product=8177
-[ RECORD 5 ]--+-------------------------------------------------------
link_source_id | 10.3940/rina.icsotin15.2015.01
base_url       | https://doi.org/10.3940/rina.icsotin15.2015.01
terminal_url   | https://www.rina.org.uk/showproducts.html?product=7883

Site is broken in some way

## www.sciencedirect.com

-[ RECORD 1 ]--+-----------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.1016/j.jhlste.2021.100332
base_url       | https://doi.org/10.1016/j.jhlste.2021.100332
terminal_url   | https://www.sciencedirect.com/science/article/abs/pii/S1473837621000332
-[ RECORD 2 ]--+-----------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.1016/j.hazadv.2021.100006
base_url       | https://doi.org/10.1016/j.hazadv.2021.100006
terminal_url   | https://www.sciencedirect.com/science/article/pii/S2772416621000061/pdfft?md5=e51bfd495bb53073c7a379d25cb11a32&pid=1-s2.0-S2772416621000061-main.pdf
-[ RECORD 3 ]--+-----------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.1016/b978-0-12-822844-9.00009-8
base_url       | https://doi.org/10.1016/b978-0-12-822844-9.00009-8
terminal_url   | https://www.sciencedirect.com/science/article/pii/B9780128228449000098
-[ RECORD 4 ]--+-----------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.1016/j.colcom.2021.100490
base_url       | https://doi.org/10.1016/j.colcom.2021.100490
terminal_url   | https://www.sciencedirect.com/science/article/abs/pii/S2215038221001308
-[ RECORD 5 ]--+-----------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.1016/b978-0-323-85245-6.00012-6
base_url       | https://doi.org/10.1016/b978-0-323-85245-6.00012-6
terminal_url   | https://www.sciencedirect.com/science/article/pii/B9780323852456000126

These no-pdf-url ones seem to just be not OA, which is expected for much of the
domain.

## repository.dri.ie

    link_source_id     |               base_url                |                terminal_url                 
-----------------------+---------------------------------------+---------------------------------------------
 10.7486/dri.t148v5941 | https://doi.org/10.7486/dri.t148v5941 | https://repository.dri.ie/catalog/t148v5941
 10.7486/dri.2z119c98f | https://doi.org/10.7486/dri.2z119c98f | https://repository.dri.ie/catalog/2z119c98f
 10.7486/dri.qf8621102 | https://doi.org/10.7486/dri.qf8621102 | https://repository.dri.ie/catalog/qf8621102
 10.7486/dri.js95m457t | https://doi.org/10.7486/dri.js95m457t | https://repository.dri.ie/catalog/js95m457t
 10.7486/dri.c534vb726 | https://doi.org/10.7486/dri.c534vb726 | https://repository.dri.ie/catalog/c534vb726

"Digital repository of Ireland"

Historical scanned content. Bespoke site. Fixed.

NOTE: recrawl/retry this domain

## www.frontiersin.org

-[ RECORD 1 ]--+------------------------------------------------------------------------------------------------------------------
link_source_id | 10.3389/978-2-88971-147-5
base_url       | https://doi.org/10.3389/978-2-88971-147-5
terminal_url   | https://www.frontiersin.org/research-topics/9081/neuroimaging-approaches-to-the-study-of-tinnitus-and-hyperacusis
-[ RECORD 2 ]--+------------------------------------------------------------------------------------------------------------------
link_source_id | 10.3389/fnins.2021.722592
base_url       | https://doi.org/10.3389/fnins.2021.722592
terminal_url   | https://www.frontiersin.org/articles/10.3389/fnins.2021.722592/full
-[ RECORD 3 ]--+------------------------------------------------------------------------------------------------------------------
link_source_id | 10.3389/fcell.2021.683209
base_url       | https://doi.org/10.3389/fcell.2021.683209
terminal_url   | https://www.frontiersin.org/articles/10.3389/fcell.2021.683209/full
-[ RECORD 4 ]--+------------------------------------------------------------------------------------------------------------------
link_source_id | 10.3389/fmicb.2021.692474
base_url       | https://doi.org/10.3389/fmicb.2021.692474
terminal_url   | https://www.frontiersin.org/articles/10.3389/fmicb.2021.692474/full
-[ RECORD 5 ]--+------------------------------------------------------------------------------------------------------------------
link_source_id | 10.3389/fneur.2021.676527
base_url       | https://doi.org/10.3389/fneur.2021.676527
terminal_url   | https://www.frontiersin.org/articles/10.3389/fneur.2021.676527/full

All the `/research-topics/` URLs are out of scope.

NOTE: recrawl missing frontiersin.org articles for PDFs
NOTE: recrawl missing frontiersin.org articles for XML (?)

-------

## direct.mit.edu

Previously "not available" (2021-05_daily_improvements.md)

## figshare.com

-[ RECORD 1 ]--+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.6084/m9.figshare.15052236.v6
base_url       | https://doi.org/10.6084/m9.figshare.15052236.v6
terminal_url   | https://figshare.com/articles/software/RCL-tree_rar/15052236/6
-[ RECORD 2 ]--+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.6084/m9.figshare.14907846.v5
base_url       | https://doi.org/10.6084/m9.figshare.14907846.v5
terminal_url   | https://figshare.com/articles/book/Conservation_of_Limestone_Ecosystems_of_Malaysia_Part_I_Acknowledgements_Methodology_Overview_of_limestone_outcrops_in_Malaysia_References_Detailed_information_on_limestone_outcrops_of_the_states_Johor_Negeri_Sembilan_Terengganu_Selangor_Pe/14907846/5
-[ RECORD 3 ]--+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.6084/m9.figshare.15157614.v1
base_url       | https://doi.org/10.6084/m9.figshare.15157614.v1
terminal_url   | https://figshare.com/articles/software/code_for_NN-A72265C/15157614/1
-[ RECORD 4 ]--+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.6084/m9.figshare.15172926.v1
base_url       | https://doi.org/10.6084/m9.figshare.15172926.v1
terminal_url   | https://figshare.com/articles/preprint/History_of_the_internet/15172926/1
-[ RECORD 5 ]--+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.6084/m9.figshare.16532574.v1
base_url       | https://doi.org/10.6084/m9.figshare.16532574.v1
terminal_url   | https://figshare.com/articles/media/Helen_McConnell_How_many_trees_do_you_think_you_have_planted_/16532574/1

NOTE: can determine from the redirect URL, I guess. This is helpful for ingest!
Could also potentially correct fatcat release_type using this info.

We seem to be getting the ones we can (eg, papers) just fine

## hkvalidate.perfdrive.com

Should be skipping/bailing on this domain, but not for some reason.

-[ RECORD 1 ]--+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.3847/1538-4357/ac05cc
base_url       | https://doi.org/10.3847/1538-4357/ac05cc
terminal_url   | https://hkvalidate.perfdrive.com/?ssa=1716a049-aeaa-4a89-8f82-bd733adaa2e7&ssb=43981203877&ssc=https%3A%2F%2Fiopscience.iop.org%2Farticle%2F10.3847%2F1538-4357%2Fac05cc&ssi=0774dd12-8427-4e27-a2ac-759c8cc2ec0e&ssk=support@shieldsquare.com&ssm=07370915269044035109047683305266&ssn=e69c743cc3d66619f960f924b562160d637e8d7f1b0f-d3bb-44d4-b075ed&sso=75a8bd85-4a097fb40f99bfb9c97b0a4ca0a38fd6d79513a466e82cc7&ssp=92054607321628531005162856888275586&ssq=33809984098158010864140981653938424553916&ssr=MjA3LjI0MS4yMjUuMTM5&sst=Mozilla/5.0%20(Windows%20NT%2010.0;%20Win64;%20x64)%20AppleWebKit/537.36%20(KHTML,%20like%20Gecko)%20Chrome/74.0.3729.169%20Safari/537.36&ssv=&ssw=
-[ RECORD 2 ]--+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.3847/1538-4357/ac0429
base_url       | https://doi.org/10.3847/1538-4357/ac0429
terminal_url   | https://hkvalidate.perfdrive.com/?ssa=12bca70d-0af4-4241-9c9b-384befd96a88&ssb=92559232428&ssc=https%3A%2F%2Fiopscience.iop.org%2Farticle%2F10.3847%2F1538-4357%2Fac0429&ssi=cff72ab0-8427-4acd-a0e7-db1b04cf7ce7&ssk=support@shieldsquare.com&ssm=27895673282814430105287068829605&ssn=9af36a8e10efd239c9367a2f31dde500f7455c4d5f45-bf11-4b99-ad29ea&sso=26bd22d2-b23e1bd9558f2fd9ed0768ef1acecb24715d1d463328a229&ssp=16502500621628222613162823304820671&ssq=11469693950387070477339503456478590533604&ssr=MjA3LjI0MS4yMjUuMTYw&sst=Mozilla/5.0%20(Windows%20NT%2010.0;%20Win64;%20x64)%20AppleWebKit/537.36%20(KHTML,%20like%20Gecko)%20Chrome/74.0.3729.169%20Safari/537.36&ssv=&ssw=
-[ RECORD 3 ]--+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.1149/1945-7111/ac1a85
base_url       | https://doi.org/10.1149/1945-7111/ac1a85
terminal_url   | https://hkvalidate.perfdrive.com/?ssa=b0fef51a-0f44-476e-b951-3341bde6aa67&ssb=84929220393&ssc=https%3A%2F%2Fiopscience.iop.org%2Farticle%2F10.1149%2F1945-7111%2Fac1a85&ssi=48c05577-8427-4421-acd3-735ca29a46e6&ssk=support@shieldsquare.com&ssm=81129482524077974103852241068134&ssn=cf6c261d2b20d518b2ebe57e40ffaec9ab4cd1955dcb-7877-4f5b-bc3b1e&sso=1d196cae-6850f1ed8143e460f2bfbb61a8ae15cfe6b53d3bcdc528ca&ssp=99289867941628195224162819241830491&ssq=16897595632212421273956322948987630170313&ssr=MjA3LjI0MS4yMjUuMjM2&sst=Mozilla/5.0%20(Windows%20NT%2010.0;%20Win64;%20x64)%20AppleWebKit/537.36%20(KHTML,%20like%20Gecko)%20Chrome/74.0.3729.169%20Safari/537.36&ssv=&ssw=
-[ RECORD 4 ]--+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.35848/1882-0786/ac1b0d
base_url       | https://doi.org/10.35848/1882-0786/ac1b0d
terminal_url   | https://hkvalidate.perfdrive.com/?ssa=6debdd23-c46b-4b40-b73c-d5540f04454e&ssb=95627212532&ssc=https%3A%2F%2Fiopscience.iop.org%2Farticle%2F10.35848%2F1882-0786%2Fac1b0d&ssi=78b34ff9-8427-4d07-a0db-78a3aa2c7332&ssk=support@shieldsquare.com&ssm=54055111549093989106852695053789&ssn=cb51949e15a02cb99a8d0b57c4d06327b72e8d5c87a8-d006-4ffa-939ffb&sso=1b7fd62d-8107746fe28fca252fd45ffa403937e272bf75b452b68d4a&ssp=77377533171628212164162820021422494&ssq=02679025218797637682252187852000657274192&ssr=MjA3LjI0MS4yMzMuMTIx&sst=Mozilla/5.0%20(Windows%20NT%2010.0;%20Win64;%20x64)%20AppleWebKit/537.36%20(KHTML,%20like%20Gecko)%20Chrome/74.0.3729.169%20Safari/537.36&ssv=&ssw=
-[ RECORD 5 ]--+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.3847/1538-4357/ac05ba
base_url       | https://doi.org/10.3847/1538-4357/ac05ba
terminal_url   | https://hkvalidate.perfdrive.com/?ssa=f127eb3d-6a05-459d-97f2-499715c04b13&ssb=06802230353&ssc=https%3A%2F%2Fiopscience.iop.org%2Farticle%2F10.3847%2F1538-4357%2Fac05ba&ssi=8d087719-8427-4046-91fb-5e96af401560&ssk=support@shieldsquare.com&ssm=21056861072205974105064006574997&ssn=d05a73cff6d9af57acd6e2c366e716176752e1164d39-b9a7-408c-837d11&sso=d3f38d1e-a562a19195042d7e471a5e4fab03b6ca16ff1711c7c61804&ssp=68781137401628744693162877909483738&ssq=79454859841502433261398415426689546750534&ssr=MjA3LjI0MS4yMzIuMTg5&sst=Mozilla/5.0%20(Windows%20NT%2010.0;%20Win64;%20x64)%20AppleWebKit/537.36%20(KHTML,%20like%20Gecko)%20Chrome/74.0.3729.169%20Safari/537.36&ssv=&ssw=

Was failing to check against blocklist again at the end of attempts.

Could retry all these to update status, but probably not worth it.

## jov.arvojournals.org

    link_source_id     |               base_url                |                        terminal_url                         
-----------------------+---------------------------------------+-------------------------------------------------------------
 10.1167/jov.21.9.1933 | https://doi.org/10.1167/jov.21.9.1933 | https://jov.arvojournals.org/article.aspx?articleid=2777021
 10.1167/jov.21.9.2910 | https://doi.org/10.1167/jov.21.9.2910 | https://jov.arvojournals.org/article.aspx?articleid=2777561
 10.1167/jov.21.9.1895 | https://doi.org/10.1167/jov.21.9.1895 | https://jov.arvojournals.org/article.aspx?articleid=2777057
 10.1167/jov.21.9.2662 | https://doi.org/10.1167/jov.21.9.2662 | https://jov.arvojournals.org/article.aspx?articleid=2777793
 10.1167/jov.21.9.2246 | https://doi.org/10.1167/jov.21.9.2246 | https://jov.arvojournals.org/article.aspx?articleid=2777441

These seem to just not be published/available yet.

But they also use watermark.silverchair.com

NOTE: re-crawl (force-retry?) all non-recent papers with fatcat-ingest
NOTE: for watermark.silverchair.com terminal bad-status, re-crawl from initial URL (base_url) using heritrix

## kiss.kstudy.com

Previously unable to download (2021-05_daily_improvements.md)

## open.library.ubc.ca

   link_source_id   |              base_url              |                                   terminal_url
--------------------+------------------------------------+----------------------------------------------------------------------------------
 10.14288/1.0400664 | https://doi.org/10.14288/1.0400664 | https://open.library.ubc.ca/collections/bcnewspapers/nelsondaily/items/1.0400664
 10.14288/1.0401189 | https://doi.org/10.14288/1.0401189 | https://open.library.ubc.ca/collections/bcnewspapers/nelsondaily/items/1.0401189
 10.14288/1.0401487 | https://doi.org/10.14288/1.0401487 | https://open.library.ubc.ca/cIRcle/collections/48630/items/1.0401487
 10.14288/1.0400994 | https://doi.org/10.14288/1.0400994 | https://open.library.ubc.ca/collections/bcnewspapers/nelsondaily/items/1.0400994
 10.14288/1.0401312 | https://doi.org/10.14288/1.0401312 | https://open.library.ubc.ca/collections/bcnewspapers/nelsondaily/items/1.0401312

Historical newspapers, out of scope?

Video content:
https://open.library.ubc.ca/cIRcle/collections/48630/items/1.0401487

Another video: https://open.library.ubc.ca/cIRcle/collections/48630/items/1.0400764

NOTE: add video link to alternative content demo ingest: https://open.library.ubc.ca/cIRcle/collections/48630/items/1.0400764
NOTE: handle this related withdrawn notice? https://open.library.ubc.ca/cIRcle/collections/48630/items/1.0401512


## panor.ru

     link_source_id      |                base_url                 |                                                                            terminal_url
-------------------------+-----------------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------
 10.33920/med-14-2108-06 | https://doi.org/10.33920/med-14-2108-06 | https://panor.ru/articles/otsenka-dinamiki-pokazateley-morfofunktsionalnykh-kharakteristik-kozhi-upatsientov-s-spr-pod-vliyaniem-kompleksnoy-fototerapii/66351.html
 10.33920/nik-02-2105-01 | https://doi.org/10.33920/nik-02-2105-01 | https://panor.ru/articles/innovatsionnost-obrazovatelnykh-tekhnologiy-kak-istoricheski-oposredovannyy-fenomen/65995.html
 10.33920/pro-1-2101-10  | https://doi.org/10.33920/pro-1-2101-10  | https://panor.ru/articles/obespechenie-bezopasnosti-na-promyshlennykh-predpriyatiyakh-s-pomoshchyu-sredstv-individualnoy-zashchity/66299.html
 10.33920/sel-4-2008-04  | https://doi.org/10.33920/sel-4-2008-04  | https://panor.ru/articles/osobennosti-regulirovaniya-zemelnykh-otnosheniy-na-prigranichnykh-territoriyakh-rossiyskoy-federatsii/66541.html
 10.33920/pro-2-2104-03  | https://doi.org/10.33920/pro-2-2104-03  | https://panor.ru/articles/organizatsiya-samorazvivayushchegosya-proizvodstva-v-realnykh-usloviyakh/65054.html

"The full version of the article is available only to subscribers of the journal"

Paywall

## peerj.com

Previously: this is HTML of reviews (2021-05_daily_improvements.md)

NOTE: Should be HTML ingest, possibly special case scope

## publons.com

Previously: this is HTML (2021-05_daily_improvements.md)

NOTE: Should be HTML ingest, possibly special case scope (length of works)

## stm.bookpi.org

       link_source_id        |                  base_url                   |                    terminal_url                    
-----------------------------+---------------------------------------------+----------------------------------------------------
 10.9734/bpi/nfmmr/v7/11547d | https://doi.org/10.9734/bpi/nfmmr/v7/11547d | https://stm.bookpi.org/NFMMR-V7/article/view/3231
 10.9734/bpi/ecafs/v1/9773d  | https://doi.org/10.9734/bpi/ecafs/v1/9773d  | https://stm.bookpi.org/ECAFS-V1/article/view/3096
 10.9734/bpi/mpebm/v5/3391f  | https://doi.org/10.9734/bpi/mpebm/v5/3391f  | https://stm.bookpi.org/MPEBM-V5/article/view/3330
 10.9734/bpi/castr/v13/3282f | https://doi.org/10.9734/bpi/castr/v13/3282f | https://stm.bookpi.org/CASTR-V13/article/view/2810
 10.9734/bpi/hmms/v13        | https://doi.org/10.9734/bpi/hmms/v13        | https://stm.bookpi.org/HMMS-V13/issue/view/274

These are... just abstracts of articles within a book? Weird. Maybe sketchy? DOIs via Crossref

## www.cabi.org

      link_source_id      |                 base_url                 |                    terminal_url
--------------------------+------------------------------------------+----------------------------------------------------
 10.1079/dfb/20133414742  | https://doi.org/10.1079/dfb/20133414742  | https://www.cabi.org/cabreviews/review/20133414742
 10.1079/dmpd/20056500471 | https://doi.org/10.1079/dmpd/20056500471 | https://www.cabi.org/cabreviews/review/20056500471
 10.1079/dmpp/20056600544 | https://doi.org/10.1079/dmpp/20056600544 | https://www.cabi.org/cabreviews/review/20056600544
 10.1079/dmpd/20056500117 | https://doi.org/10.1079/dmpd/20056500117 | https://www.cabi.org/cabreviews/review/20056500117
 10.1079/dmpp20056600337  | https://doi.org/10.1079/dmpp20056600337  | https://www.cabi.org/cabreviews/review/20056600337

Reviews? but just abstracts?

## www.cureus.com

-[ RECORD 1 ]--+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.7759/cureus.17547
base_url       | https://doi.org/10.7759/cureus.17547
terminal_url   | https://www.cureus.com/articles/69542-tramadol-induced-jerks
-[ RECORD 2 ]--+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.7759/cureus.16867
base_url       | https://doi.org/10.7759/cureus.16867
terminal_url   | https://www.cureus.com/articles/66793-advanced-squamous-cell-carcinoma-of-gall-bladder-masquerading-as-liver-abscess-with-review-of-literature-review-on-advanced-biliary-tract-cancer
-[ RECORD 3 ]--+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.7759/cureus.17425
base_url       | https://doi.org/10.7759/cureus.17425
terminal_url   | https://www.cureus.com/articles/67438-attitudes-and-knowledge-of-medical-students-towards-healthcare-for-lesbian-gay-bisexual-and-transgender-seniors-impact-of-a-case-based-discussion-with-facilitators-from-the-community
-[ RECORD 4 ]--+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.7759/cureus.17313
base_url       | https://doi.org/10.7759/cureus.17313
terminal_url   | https://www.cureus.com/articles/67258-utilizing-google-trends-to-track-online-interest-in-elective-hand-surgery-during-the-covid-19-pandemic
-[ RECORD 5 ]--+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
link_source_id | 10.7759/cureus.16943
base_url       | https://doi.org/10.7759/cureus.16943
terminal_url   | https://www.cureus.com/articles/19364-small-bowel-obstruction-a-rare-presentation-of-the-inferior-pancreaticoduodenal-artery-pseudoaneurysm-bleed

Ugh, stupid "email to get PDF". but ingest seems to work anyways?

NOTE: re-crawl/re-ingest all (eg, fatcat-ingest or similar)

## www.e-manuscripta.ch

        link_source_id        |                   base_url                   |                           terminal_url
------------------------------+----------------------------------------------+-------------------------------------------------------------------
 10.7891/e-manuscripta-114031 | https://doi.org/10.7891/e-manuscripta-114031 | https://www.e-manuscripta.ch/swa/doi/10.7891/e-manuscripta-114031
 10.7891/e-manuscripta-112064 | https://doi.org/10.7891/e-manuscripta-112064 | https://www.e-manuscripta.ch/zut/doi/10.7891/e-manuscripta-112064
 10.7891/e-manuscripta-112176 | https://doi.org/10.7891/e-manuscripta-112176 | https://www.e-manuscripta.ch/zut/doi/10.7891/e-manuscripta-112176
 10.7891/e-manuscripta-115200 | https://doi.org/10.7891/e-manuscripta-115200 | https://www.e-manuscripta.ch/swa/doi/10.7891/e-manuscripta-115200
 10.7891/e-manuscripta-114008 | https://doi.org/10.7891/e-manuscripta-114008 | https://www.e-manuscripta.ch/swa/doi/10.7891/e-manuscripta-114008

Historical docs, single pages, but do have full PDF downloads.

NOTE: re-ingest

## www.inderscience.com

Previously: paywall (2021-05_daily_improvements.md)

## www.un-ilibrary.org

       link_source_id       |                  base_url                  |                        terminal_url                         
----------------------------+--------------------------------------------+-------------------------------------------------------------
 10.18356/9789210550307     | https://doi.org/10.18356/9789210550307     | https://www.un-ilibrary.org/content/books/9789210550307
 10.18356/9789210586719c011 | https://doi.org/10.18356/9789210586719c011 | https://www.un-ilibrary.org/content/books/9789210586719c011
 10.18356/9789210058575c014 | https://doi.org/10.18356/9789210058575c014 | https://www.un-ilibrary.org/content/books/9789210058575c014
 10.18356/9789210550307c020 | https://doi.org/10.18356/9789210550307c020 | https://www.un-ilibrary.org/content/books/9789210550307c020
 10.18356/9789213631423c005 | https://doi.org/10.18356/9789213631423c005 | https://www.un-ilibrary.org/content/books/9789213631423c005

Books and chapters. Doesn't seem to have actual download ability?

# Re-Ingest / Re-Crawl

Using fatcat-ingest helper tool.

- www.isca-speech.org doi_prefix:10.21437
    doi:* doi_prefix:10.21437 in_ia:false
    9,233
    ./fatcat_ingest.py --allow-non-oa query 'doi:* doi_prefix:10.21437' > /srv/fatcat/tasks/2021-09-03_ingest_isca.json
    => Counter({'ingest_request': 9221, 'elasticsearch_release': 9221, 'estimate': 9221})
- repository.dri.ie doi_prefix:10.7486
    doi:* in_ia:false doi_prefix:10.7486
    56,532
    ./fatcat_ingest.py --allow-non-oa query 'doi:* doi_prefix:10.7486' > /srv/fatcat/tasks/2021-09-03_ingest_dri.json
    => Counter({'ingest_request': 56532, 'elasticsearch_release': 56532, 'estimate': 56532})
- *.arvojournals.org doi_prefix:10.1167 (force recrawl if no-pdf-link)
    25,598
    many are meeting abstracts
    ./fatcat_ingest.py --allow-non-oa query doi_prefix:10.1167 > /srv/fatcat/tasks/2021-09-03_ingest_arvo.json
    => Counter({'ingest_request': 25598, 'elasticsearch_release': 25598, 'estimate': 25598})
- www.cureus.com doi_prefix:10.7759
    1,537
    ./fatcat_ingest.py --allow-non-oa query doi_prefix:10.7759 > /srv/fatcat/tasks/2021-09-03_ingest_cureus.json
    => Counter({'ingest_request': 1535, 'elasticsearch_release': 1535, 'estimate': 1535})
- www.e-manuscripta.ch doi_prefix:10.7891 10.7891/e-manuscripta
    110,945
    TODO: all are marked 'unpublished', but that is actually probably right?
- www.frontiersin.org doi_prefix:10.3389 (both PDF and XML!)
    doi:* in_ia:false doi_prefix:10.3389
    212,370
    doi:10.3389/conf.*   => most seem to be just abstracts? how many like this?
    container_id:kecnf6vtpngn7j2avgfpdyw5ym => "topics" (2.2k)
    fatcat-cli search release 'doi:* in_ia:false doi_prefix:10.3389 !container_id:kecnf6vtpngn7j2avgfpdyw5ym' --index-json -n0 | jq '[.ident, .container_id, .doi] | @tsv' -r | rg -v 10.3389/conf | pv -l | gzip > frontiers_to_crawl.tsv.gz
    => 191k
    but many might be components? this is actually kind of a mess
    fatcat-cli search release 'doi:* in_ia:false doi_prefix:10.3389 !container_id:kecnf6vtpngn7j2avgfpdyw5ym !type:component stage:published' --index-json -n0 | jq '[.ident, .container_id, .doi] | @tsv' -r | rg -v 10.3389/conf | pv -l | gzip > frontiers_to_crawl.tsv.gz
    => 19.2k
    ./fatcat_ingest.py --allow-non-oa query 'doi:* in_ia:false doi_prefix:10.3389 !container_id:kecnf6vtpngn7j2avgfpdyw5ym !type:component stage:published' | rg -v 10.3389/conf > /srv/fatcat/tasks/2021-09-03_frontiers.json

# Remaining Tasks / Domains (TODO)

more complex crawling/content:
- add video link to alternative content demo ingest: https://open.library.ubc.ca/cIRcle/collections/48630/items/1.0400764
- watermark.silverchair.com: if terminal-bad-status, then do recrawl via heritrix with base_url
- www.morressier.com: interesting site for rich web crawling/preservation (video+slides+data)
- doi.ala.org.au: possible dataset ingest source
- peerj.com, at least reviews, should be HTML ingest? or are some PDF?
- publons.com should be HTML ingest, possibly special case for scope
- frontiersin.org: any 'component' releases with PDF file are probably a metadata bug

other tasks:
- handle this related withdrawn notice? https://open.library.ubc.ca/cIRcle/collections/48630/items/1.0401512
- push/deploy sandcrawler changes
