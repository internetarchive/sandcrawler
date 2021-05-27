
Summary of top large broken domains (2021-04-21 "30 day" snapshot):

## acervus.unicamp.br

                domain                 |         status          | count  
---------------------------------------+-------------------------+--------
    acervus.unicamp.br                    |                         |   1967
    acervus.unicamp.br                    | no-pdf-link             |   1853

select * from ingest_file_result where updated >= '2021-03-01' and terminal_url like '%acervus.unicamp.br%' and status = 'no-pdf-link' limit 5;

http://acervus.unicamp.br/index.asp?codigo_sophia=963332

seems like many of these were captures with a blank page? or a redirect to
the homepage?

http://web.archive.org/web/20200129110523/http://acervus.unicamp.br/index.html

messy, going to move on.


## apex.ipk-gatersleben.de

apex.ipk-gatersleben.de               |                         |   1253
apex.ipk-gatersleben.de               | no-pdf-link             |   1132

select * from ingest_file_result where updated >= '2021-03-01' and terminal_url like '%apex.ipk-gatersleben.de%' and status = 'no-pdf-link' limit 5;

https://doi.org/10.25642/ipk/rescoll/4886
https://apex.ipk-gatersleben.de/apex/f?p=PGRDOI:RESOLVE:::NO:RP:DOI:10.25642/IPK/RESCOLL/7331

seem to be datasets/species, not articles.

prefix: 10.25642/ipk

## crossref.org

     apps.crossref.org                     |                         |   4693
     apps.crossref.org                     | no-pdf-link             |   4075

https://doi.org/10.1515/9781501747045-013
https://apps.crossref.org/coaccess/coaccess.html?doi=10.1515%2F9781501747045-013

Derp, they are doing a dynamic/AJAX thing, so access links are not in the HTML.

## openeditiong

     books.openedition.org                 |                         |   1784
     books.openedition.org                 | no-pdf-link             |   1466

https://doi.org/10.4000/books.pul.34492
https://books.openedition.org/pul/34492

these are not actually OA books (or at least, not all are)

## chemrxiv.org (figshare)

     chemrxiv.org                          |                         |    857
     chemrxiv.org                          | no-pdf-link             |    519

https://doi.org/10.26434/chemrxiv.14411081
https://chemrxiv.org/articles/preprint/Prediction_and_Optimization_of_Ion_Transport_Characteristics_in_Nanoparticle-Based_Electrolytes_Using_Convolutional_Neural_Networks/14411081

these all seem to be *multi-file* entities, thus not good for single file ingest pipeline.

## direct.mit.edu

     direct.mit.edu                        |                         |    996
     direct.mit.edu                        | no-pdf-link             |    869

https://doi.org/10.7551/mitpress/14056.003.0004
https://direct.mit.edu/books/monograph/5111/chapter-abstract/3060134/Adding-Technology-to-Contact-Tracing?redirectedFrom=fulltext

"not available"

https://doi.org/10.7551/mitpress/12444.003.0004

"not available"


## dlc.library.columbia.edu

     dlc.library.columbia.edu              |                         |   4225
     dlc.library.columbia.edu              | no-pdf-link             |   2395
     dlc.library.columbia.edu              | spn2-wayback-error      |   1568

https://doi.org/10.7916/d8-506w-kk49
https://dlc.library.columbia.edu/durst/cul:18931zcrk9

document repository.
this one goes to IA! actually many seem to.
added extractor, should re-ingest with:

    publisher:"Columbia University" doi_prefix:10.7916 !journal:*

actually, that is like 600k+ results and many are not digitized, so perhaps not.

## doi.ala.org.au

     doi.ala.org.au                        |                         |   2570
     doi.ala.org.au                        | no-pdf-link             |   2153

https://doi.org/10.26197/ala.811d55e3-2ff4-4501-b3e7-e19249507052
https://doi.ala.org.au/doi/811d55e3-2ff4-4501-b3e7-e19249507052

this is a data repository, with filesets, not papers. datacite metadata is
incorrect.

## fldeploc.dep.state.fl.us

     fldeploc.dep.state.fl.us              |                         |    774
     fldeploc.dep.state.fl.us              | no-pdf-link             |    718


https://doi.org/10.35256/ic29
http://fldeploc.dep.state.fl.us/geodb_query/fgs_doi.asp?searchCode=IC29

re-ingest with:

    # only ~800 works
    doi_prefix:10.35256 publisher:Florida

## geoscan.nrcan.gc.ca

     geoscan.nrcan.gc.ca                   |                         |   2056
     geoscan.nrcan.gc.ca                   | no-pdf-link             |   2019

https://doi.org/10.4095/295366
https://geoscan.nrcan.gc.ca/starweb/geoscan/servlet.starweb?path=geoscan/fulle.web&search1=R=295366

this is a geographic repository, not papers.

## kiss.kstudy.com

     kiss.kstudy.com                       |                         |    747
     kiss.kstudy.com                       | no-pdf-link             |    686

https://doi.org/10.22143/hss21.12.1.121
http://kiss.kstudy.com/thesis/thesis-view.asp?key=3862523

Korean. seems to not actually be theses? can't download.

## linkinghub.elsevier.com

     linkinghub.elsevier.com               |                         |   5079
     linkinghub.elsevier.com               | forbidden               |   2226
     linkinghub.elsevier.com               | spn2-wayback-error      |   1625
     linkinghub.elsevier.com               | spn2-cdx-lookup-failure |    758

skipping for now, looks like mostly 'forbidden'?

## osf.io

These are important!

     osf.io                                |                         |   3139
     osf.io                                | not-found               |   2288
     osf.io                                | spn2-wayback-error      |    582

https://doi.org/10.31219/osf.io/jux3w
https://accounts.osf.io/login?service=https://osf.io/jux3w/download

many of these are 404s by browser as well. what does that mean?

## peerj.com

     peerj.com                             |                         |    785
     peerj.com                             | no-pdf-link             |    552

https://doi.org/10.7287/peerj.11155v0.1/reviews/2
https://peerj.com/articles/11155/reviews/

these are HTML reviews, not papers

## preprints.jmir.org

     preprints.jmir.org                    |                         |    763
     preprints.jmir.org                    | no-pdf-link             |    611

https://doi.org/10.2196/preprints.22556
https://preprints.jmir.org/preprint/22556

UGH, looks simple, but javascript.

could try to re-write URL into S3 format? meh.

## psyarxiv.com (OSF?)

     psyarxiv.com                          |                         |    641
     psyarxiv.com                          | no-pdf-link             |    546

https://doi.org/10.31234/osf.io/5jaqg
https://psyarxiv.com/5jaqg/

Also infuriatingly Javascript, but can do URL hack.

Should reingest, and potentially force-recrawl:

    # about 67k
    publisher:"Center for Open Science" in_ia:false

## publons.com

     publons.com                           |                         |   6998
     publons.com                           | no-pdf-link             |   6982

https://doi.org/10.1002/jmor.21338/v2/review1
https://publons.com/publon/40260824/

These are just HTML reviews, not papers.

## saemobilus.sae.org

     saemobilus.sae.org                    |                         |    795
     saemobilus.sae.org                    | no-pdf-link             |    669

https://doi.org/10.4271/as1426c
https://saemobilus.sae.org/content/as1426c

These seem to be standards, and are not open access (paywall)

## scholar.dkyobobook.co.kr

     scholar.dkyobobook.co.kr              |                         |   1043
     scholar.dkyobobook.co.kr              | no-pdf-link             |    915

https://doi.org/10.22471/crisis.2021.6.1.18
http://scholar.dkyobobook.co.kr/searchDetail.laf?barcode=4010028199536

Korean. complex javascript, skipping.

## unreserved.rba.gov.au

     unreserved.rba.gov.au                 |                         |    823
     unreserved.rba.gov.au                 | no-pdf-link             |    821

https://doi.org/10.47688/rba_archives_2006/04129
https://unreserved.rba.gov.au/users/login

Don't need to login when I tried in browser? document repo, not papers.

## wayf.switch.ch

     wayf.switch.ch                        |                         |   1169
     wayf.switch.ch                        | no-pdf-link             |    809

https://doi.org/10.24451/arbor.11128
https://wayf.switch.ch/SWITCHaai/WAYF?entityID=https%3A%2F%2Farbor.bfh.ch%2Fshibboleth&return=https%3A%2F%2Farbor.bfh.ch%2FShibboleth.sso%2FLogin%3FSAMLDS%3D1%26target%3Dss%253Amem%253A5056fc0a97aeab16e5007ca63bede254cb5669d94173064d6c74c62a0f88b022

Loginwall

##

     www.bloomsburycollections.com         |                         |   1745
     www.bloomsburycollections.com         | no-pdf-link             |   1571

https://doi.org/10.5040/9781849664264.0008
https://www.bloomsburycollections.com/book/the-political-economies-of-media-the-transformation-of-the-global-media-industries/the-political-economies-of-media-and-the-transformation-of-the-global-media-industries

These are primarily not OA/available.

##

     www.emc2020.eu                        |                         |    791
     www.emc2020.eu                        | no-pdf-link             |    748

https://doi.org/10.22443/rms.emc2020.146
https://www.emc2020.eu/abstract/evaluation-of-different-rectangular-scan-strategies-for-hrstem-imaging.html

These are just abstracts, not papers.

## Emerald

     www.emerald.com                       |                         |   2420
     www.emerald.com                       | no-pdf-link             |   1986

https://doi.org/10.1108/ramj-11-2020-0065
https://www.emerald.com/insight/content/doi/10.1108/RAMJ-11-2020-0065/full/html

Note that these URLs are already HTML fulltext. but the PDF is also available and easy.

re-ingest:

    # only ~3k or so missing
    doi_prefix:10.1108 publisher:emerald in_ia:false is_oa:true

##

     www.humankineticslibrary.com          |                         |   1122
     www.humankineticslibrary.com          | no-pdf-link             |    985

https://doi.org/10.5040/9781718206625.ch-002
https://www.humankineticslibrary.com/encyclopedia-chapter?docid=b-9781718206625&tocid=b-9781718206625-chapter2

paywall

##

     www.inderscience.com                  |                         |   1532
     www.inderscience.com                  | no-pdf-link             |   1217

https://doi.org/10.1504/ijdmb.2020.10036342
https://www.inderscience.com/info/ingeneral/forthcoming.php?jcode=ijdmb

paywall

##

     www.ingentaconnect.com                |                         |    885
     www.ingentaconnect.com                | no-pdf-link             |    783

https://doi.org/10.15258/sst.2021.49.1.07
https://www.ingentaconnect.com/content/ista/sst/pre-prints/content-7_sst.2021.49.1_63-71;jsessionid=1joc5mmi1juht.x-ic-live-02

Annoying javascript, but easy to work around.

re-ingest:

    # only a couple hundred; also re-ingest
    doi_prefix:10.15258 in_ia:false year:>2018

##

     www.nomos-elibrary.de                 |                         |   2235
     www.nomos-elibrary.de                 | no-pdf-link             |   1128
     www.nomos-elibrary.de                 | spn2-wayback-error      |    559

https://doi.org/10.5771/9783748907084-439
https://www.nomos-elibrary.de/10.5771/9783748907084-439/verzeichnis-der-autorinnen-und-autoren

Javascript obfuscated download button?

##

     www.oecd-ilibrary.org                 |                         |   3046
     www.oecd-ilibrary.org                 | no-pdf-link             |   2869

https://doi.org/10.1787/543e84ed-en
https://www.oecd-ilibrary.org/development/applying-evaluation-criteria-thoughtfully_543e84ed-en

Paywall.

##

     www.osapublishing.org                 |                         |    821
     www.osapublishing.org                 | no-pdf-link             |    615

https://doi.org/10.1364/boe.422199
https://www.osapublishing.org/boe/abstract.cfm?doi=10.1364/BOE.422199

Some of these are "pre-registered" DOIs, not published yet. Many of the
remaining are actually HTML articles, and/or have some stuff in the
`citation_pdf_url`. A core problem is captchas.

Have started adding support to fatcat for HTML crawl type based on container.

re-ingest:

    container_twtpsm6ytje3nhuqfu3pa7ca7u (optica)
    container_cg4vcsfty5dfvgmat5wm62wgie (optics express)

##

     www.oxfordscholarlyeditions.com       |                         |    759
     www.oxfordscholarlyeditions.com       | no-pdf-link             |    719

https://doi.org/10.1093/oseo/instance.00266789
https://www.oxfordscholarlyeditions.com/view/10.1093/actrade/9780199593668.book.1/actrade-9780199593668-div1-27

loginwall/paywall

##

     www.schweizerbart.de                  |                         |    730
     www.schweizerbart.de                  | no-pdf-link             |    653

https://doi.org/10.1127/zfg/40/1996/461
https://www.schweizerbart.de/papers/zfg/detail/40/97757/Theoretical_model_of_surface_karstic_processes?af=crossref

paywall

##

     www.sciencedirect.com                 |                         |  14757
     www.sciencedirect.com                 | no-pdf-link             |  12733
     www.sciencedirect.com                 | spn2-wayback-error      |   1503

https://doi.org/10.1016/j.landurbplan.2021.104104
https://www.sciencedirect.com/science/article/pii/S0169204621000670

Bunch of crazy new hacks, but seems to be working!

re-ingest:

    # to start! about 50k
    doi_prefix:10.1016 is_oa:true year:2021

##

     www.sciendo.com                       |                         |   1955
     www.sciendo.com                       | no-pdf-link             |   1176

https://doi.org/10.2478/awutm-2019-0012
https://www.sciendo.com/article/10.2478/awutm-2019-0012

uses lots of javascript, hard to scrape.


## Others (for reference)

    |                         | 725990
    | no-pdf-link             | 209933
    | success                 | 206134
    | spn2-wayback-error      | 127015
    | spn2-cdx-lookup-failure |  53384
    | blocked-cookie          |  35867
    | link-loop               |  25834
    | too-many-redirects      |  16430
    | redirect-loop           |  14648
    | forbidden               |  13794
    | terminal-bad-status     |   8055
    | not-found               |   6399
    | remote-server-error     |   2402
    | wrong-mimetype          |   2011
    | spn2-error:unauthorized |    912
    | bad-redirect            |    555
    | read-timeout            |    530

## Re-ingests

All the above combined:

    container_twtpsm6ytje3nhuqfu3pa7ca7u (optica)
    container_cg4vcsfty5dfvgmat5wm62wgie (optics express)

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --ingest-type html container --container-id twtpsm6ytje3nhuqfu3pa7ca7u
    => Counter({'ingest_request': 1142, 'elasticsearch_release': 1142, 'estimate': 1142, 'kafka': 1142})

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --ingest-type html container --container-id cg4vcsfty5dfvgmat5wm62wgie 
    => Counter({'elasticsearch_release': 33482, 'estimate': 33482, 'ingest_request': 32864, 'kafka': 32864})

    # only ~800 works
    doi_prefix:10.35256 publisher:Florida

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --allow-non-oa query "doi_prefix:10.35256 publisher:Florida"
    => Counter({'ingest_request': 843, 'elasticsearch_release': 843, 'estimate': 843, 'kafka': 843})

    # only ~3k or so missing
    doi_prefix:10.1108 publisher:emerald in_ia:false is_oa:true

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org query "doi_prefix:10.1108 publisher:emerald"
    => Counter({'ingest_request': 3812, 'elasticsearch_release': 3812, 'estimate': 3812, 'kafka': 3812})


    # only a couple hundred; also re-ingest
    doi_prefix:10.15258 in_ia:false year:>2018

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --allow-non-oa --force-recrawl query "doi_prefix:10.15258 year:>2018"
    => Counter({'ingest_request': 140, 'elasticsearch_release': 140, 'estimate': 140, 'kafka': 140})

    # to start! about 50k
    doi_prefix:10.1016 is_oa:true year:2020
    doi_prefix:10.1016 is_oa:true year:2021

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org query "doi_prefix:10.1016 year:2020"
    => Counter({'ingest_request': 75936, 'elasticsearch_release': 75936, 'estimate': 75936, 'kafka': 75936})

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org query "doi_prefix:10.1016 year:2021"
    => Counter({'ingest_request': 54824, 'elasticsearch_release': 54824, 'estimate': 54824, 'kafka': 54824})

    pmcid:* year:2018
    pmcid:* year:2019

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --force-recrawl query "pmcid:* year:2018"
    => Counter({'ingest_request': 25366, 'elasticsearch_release': 25366, 'estimate': 25366, 'kafka': 25366})

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --force-recrawl query "pmcid:* year:2019"
    => Counter({'ingest_request': 55658, 'elasticsearch_release': 55658, 'estimate': 55658, 'kafka': 55658})

