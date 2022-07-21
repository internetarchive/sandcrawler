
## HTML `html-resource-no-capture` Fixes

Tracing down some `html-resource-no-capture` issues. Eg, `javascript:` resources causing errors.

SQL query:

    select * from ingest_file_result where ingest_type = 'html' and status = 'html-resource-no-capture' limit 100;
    select * from ingest_file_result where ingest_type = 'html' and status = 'html-resource-no-capture' order by random() limit 100;

    select count(*) from ingest_file_result where ingest_type = 'html' and status = 'html-resource-no-capture';
    => 210,528

http://agroengineering.it/index.php/jae/article/view/568/609
- old capture, from `20171017204935`
- missing .css file; seems like an actual case of missing content?
- TODO: re-crawl/re-ingest when CDX is old

https://www.karger.com/Article/FullText/484130
- missing: https://www.karger.com/WebMaterial/ShowThumbnail/895999?imgType=2
- resource is live
- this was from DOI-LANDING crawl, no resources captured
- TODO: re-crawl

https://www.mdpi.com/1996-1073/13/21/5563/htm
- missing: https://www.mdpi.com/1996-1073/13/21/5563/htm
- common crawl capture; no/few resources?
- TODO: re-crawl

http://www.scielo.br/scielo.php?script=sci_arttext&pid=S0100-736X2013000500011&lng=en&tlng=en
- missing: http://www.scielo.br/img/revistas/pvb/v33n5/a11tab01.jpg
    not on live web
- old (2013) wide crawl
- TODO: re-crawl

http://g3journal.org/lookup/doi/10.1534/g3.116.027730
- missing: http://www.g3journal.org/sites/default/files/highwire/ggg/6/8/2553/embed/mml-math-4.gif
- old 2018 landing crawl (no resources)
- TODO: re-crawl

https://www.frontiersin.org/articles/10.3389/fimmu.2020.576134/full
- "error_message": "revisit record missing URI and/or DT: warc:abc.net.au-news-20220328-130654/IA-FOC-abc.net.au-news-20220618135308-00003.warc.gz offset:768320762"
- specific URL: https://www.frontiersin.org/areas/articles/js/app?v=uC9Es8wJ9fbTy8Rj4KipiyIXvhx7XEVhCTHvIrM4ShA1
- archiveteam crawl
- seems like a weird corner case. look at more 'frontiersin' articles, and re-crawl this page

https://www.frontiersin.org/articles/10.3389/fonc.2020.01386/full
- WORKING

https://doi.org/10.4000/trajectoires.2317
- redirect: https://journals.openedition.org/trajectoires/2317
- missing: "https://journals.openedition.org/trajectoires/Ce fichier n'existe pas" (note spaces)
- FIXED

http://www.scielosp.org/scielo.php?script=sci_arttext&pid=S1413-81232002000200008&lng=en&tlng=en
- WORKING

https://f1000research.com/articles/9-571/v2
- petabox-error on 'https://www.recaptcha.net/recaptcha/api.js'
- added recaptcha.net to blocklist
- still needs a re-crawl
- SPN capture, from 2020, but images were missing?
- re-capture has images (though JS still wonky)
- TODO: re-crawl with SPN2

http://bio.biologists.org/content/4/9/1163
- DOI LANDING crawl, no sub-resources
- TODO: recrawl

http://err.ersjournals.com/content/26/145/170039.full
- missing: http://err.ersjournals.com/sites/default/files/highwire/errev/26/145/170039/embed/graphic-5.gif
    on live web
- 2017 targetted heritrix crawl
- TODO: recrawl

http://www.dovepress.com/synthesis-characterization-and-antimicrobial-activity-of-an-ampicillin-peer-reviewed-article-IJN
- missing: https://www.dovepress.com/cr_data/article_fulltext/s61000/61143/img/IJN-61143-F02-Thumb.jpg
- recent archiveteam crawl
- TODO: recrawl

http://journals.ed.ac.uk/lithicstudies/article/view/1444
- missing: http://journals.ed.ac.uk/lithicstudies/article/download/1444/2078/6081
- common crawl
- TODO: recrawl

http://medisan.sld.cu/index.php/san/article/view/495
- missing: http://ftp.scu.sld.cu/galen/medisan/logos/redib.jpg
- this single resource is legit missing

seems like it probably isn't a bad idea to just re-crawl all of these with fresh SPNv2 requests

request sources:
- fatcat-changelog (doi)
- fatcat-ingest (doi)
- doaj


    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'html'
            AND ingest_file_result.status = 'html-resource-no-capture'
            AND (
                ingest_request.link_source = 'doi'
                OR ingest_request.link_source = 'doaj'
            )
    ) TO '/srv/sandcrawler/tasks/retry_html_resourcenocapture.2022-07-15.rows.json';
    => COPY 210749

    ./scripts/ingestrequest_row2json.py --force-recrawl /srv/sandcrawler/tasks/retry_html_resourcenocapture.2022-07-15.rows.json > /srv/sandcrawler/tasks/retry_html_resourcenocapture.2022-07-15.json

Try a sample of 300:

    shuf -n300 /srv/sandcrawler/tasks/retry_html_resourcenocapture.2022-07-15.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc350.us.archive.org -t sandcrawler-prod.ingest-file-requests-daily -p -1

Seeing a bunch of:

    ["doaj","wayback-content-error","https://www.frontiersin.org/article/10.3389/fphys.2020.00454/full","https://www.frontiersin.org/articles/10.3389/fphys.2020.00454/full","revisit record missing URI and/or DT: warc:foxnews.com-20220402-051934/IA-FOC-foxnews.com-20220712070651-00000.warc.gz offset:937365431"]
    ["doaj","wayback-content-error","https://www.frontiersin.org/article/10.3389/fmicb.2019.02507/full","https://www.frontiersin.org/articles/10.3389/fmicb.2019.02507/full","revisit record missing URI and/or DT: warc:foxnews.com-20220402-051934/IA-FOC-foxnews.com-20220712070651-00000.warc.gz offset:937365431"]
    ["doaj","wayback-content-error","https://www.mdpi.com/2218-1989/10/9/366","https://www.mdpi.com/2218-1989/10/9/366/htm","revisit record missing URI and/or DT: warc:foxnews.com-20220402-051934/IA-FOC-foxnews.com-20220712070651-00000.warc.gz offset:964129887"]

    "error_message": "revisit record missing URI and/or DT: warc:online.wsj.com-home-page-20220324-211958/IA-FOC-online.wsj.com-home-page-20220716075018-00001.warc.gz offset:751923069",


    ["doaj","wayback-content-error","https://www.frontiersin.org/article/10.3389/fnins.2020.00724/full","https://www.frontiersin.org/articles/10.3389/fnins.2020.00724/full","wayback payload sha1hex mismatch: 20220715222216 https://static.frontiersin.org/areas/articles/js/app?v=DfnFHSIgqDJBKQy2bbQ2S8vWyHe2dEMZ1Lg9o6vSS1g1"]

These seem to be transfer encoding issues; fixed?

    ["doaj","html-resource-no-capture","http://www.scielosp.org/scielo.php?script=sci_arttext&pid=S0021-25712013000400003&lng=en&tlng=en","https://scielosp.org/article/aiss/2013.v49n4/336-339/en/","HTML sub-resource not found: https://ssm.scielo.org/media/assets/css/scielo-print.css"]

Full batch:

    # TODO: cat /srv/sandcrawler/tasks/retry_html_resourcenocapture.2022-07-15.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc350.us.archive.org -t sandcrawler-prod.ingest-file-requests-daily -p -1

Not running the full batch for now, because there are almost all `wayback-content-error` issues.

    cat /srv/sandcrawler/tasks/retry_html_resourcenocapture.2022-07-15.json | rg -v frontiersin.org | wc -l
    114935

    cat /srv/sandcrawler/tasks/retry_html_resourcenocapture.2022-07-15.json | rg -v frontiersin.org | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc350.us.archive.org -t sandcrawler-prod.ingest-file-requests-daily -p -1


## Redirect Loops

Seems like there might have been a bug in how ingest pipeline dealt with
multiple redirects (eg, 301 to 302 or vice-versa), due to how CDX lookups and
normalization was happening.

This could be a really big deal because we have over 11 million such ingest
requests! and may even have stopped crawling domains on the basis of redirect
looping.

    select * from ingest_file_result where ingest_type = 'pdf' and status = 'redirect-loop' limit 50;

http://ieeexplore.ieee.org/iel7/7259950/7275573/07275755.pdf
- 'skip-url-blocklist'
- paywall on live web

http://www.redjournal.org/article/S0360301616308276/pdf
- redirect to 'secure.jbs.elsevierhealth.com'
- ... but re-crawling with SPNv2 worked
- TODO: reingest this entire journal with SPNv2

http://www.jmirs.org/article/S1939865415001551/pdf
- blocked-cookie (secure.jbs.elsevierhealth.com)
- RECRAWL: success

http://www.cell.com/article/S0006349510026147/pdf
- blocked-cookie (secure.jbs.elsevierhealth.com)
- TODO: try SPNv2?
- RECRAWL: success

http://infoscience.epfl.ch/record/256431/files/SPL_2018.pdf
- FIXED: success

http://www.nature.com/articles/hdy1994143.pdf
- blocked-cookie (idp.nature.com / cookies_not_supported)
- RECRAWL: gateway-timeout

http://www.thelancet.com/article/S0140673619327606/pdf
- blocked-cookie (secure.jbs.elsevierhealth.com)
- RECRAWL: success

https://pure.mpg.de/pubman/item/item_2065970_2/component/file_2065971/Haase_2014.pdf
- FIXED: success

http://hdl.handle.net/21.11116/0000-0001-B1A2-F
- FIXED: success

http://repositorio.ufba.br/ri/bitstream/ri/6072/1/%2858%29v21n6a03.pdf
- FIXED: success

http://www.jto.org/article/S1556086416329999/pdf
- blocked-cookie (secure.jbs.elsevierhealth.com)
- RECRAWL spn2: success

http://www.jahonline.org/article/S1054139X16303020/pdf
- blocked-cookie (secure.jbs.elsevierhealth.com)
- RECRAWL spn2: success

So, wow wow wow, a few things to do here:

- just re-try all these redirect-loop attempts to update status
- re-ingest all these elsevierhealth blocked crawls with SPNv2. this could take a long time!

Possibly the elsevierhealth stuff will require some deeper fiddling to crawl
correctly.

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_file_result.status = 'redirect-loop'
            -- AND ingest_request.ingest_type = 'pdf'
            AND (
                ingest_request.link_source = 'doi'
                OR ingest_request.link_source = 'doaj'
                OR ingest_request.link_source = 'unpaywall'
            )
    ) TO '/srv/sandcrawler/tasks/retry_redirectloop.2022-07-15.rows.json';
    => COPY 6611342

    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/retry_redirectloop.2022-07-15.rows.json > /srv/sandcrawler/tasks/retry_redirectloop.2022-07-15.json

Start with a sample:

    shuf -n200 /srv/sandcrawler/tasks/retry_redirectloop.2022-07-15.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc350.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

Wow that is a lot of ingest! And a healthy fraction of 'success', almost all
via unpaywall (maybe should have done DOAJ/DOI only first). Let's do this full
batch:

    cat /srv/sandcrawler/tasks/retry_redirectloop.2022-07-15.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc350.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

TODO: repeat with broader query (eg, OAI-PMH, MAG, etc).

## Other

Revist resolution failed: \"Didn't get exact CDX url/datetime match. url:https://www.cairn.info/static/images//logo/logo-cairn-negatif.png dt:20220430145322 got:CdxRow(surt='info,cairn)/static/images/logo/logo-cairn-negatif.png', datetime='20220430145322', url='https://www.cairn.info/static/images/logo/logo-cairn-negatif.png', mimetype='image/png', status_code=200, sha1b32='Y3VQOPO2NFUR2EUWNXLYGYGNZPZLQYHU', sha1hex='c6eb073dda69691d12966dd78360cdcbf2b860f4', warc_csize=10875, warc_offset=2315284914, warc_path='archiveteam_archivebot_go_20220430212134_59230631/old.worldurbancampaign.org-inf-20220430-140628-acnq5-00000.warc.gz')\""

    https://www.cairn.info/static/images//logo/logo-cairn-negatif.png   20220430145322
    https://www.cairn.info/static/images/logo/logo-cairn-negatif.png    20220430145322

Fixed!


## Broken WARC Record?

cdx line:

    net,cloudfront,d1bxh8uas1mnw7)/assets/embed.js 20220716084026 https://d1bxh8uas1mnw7.cloudfront.net/assets/embed.js warc/revisit - U5E5UA6DS5GGCHJ2IZSOIEGPN6P64JRB - - 660 751923069 online.wsj.com-home-page-20220324-211958/IA-FOC-online.wsj.com-home-page-20220716075018-00001.warc.gz

download WARC and run:

    zcat IA-FOC-online.wsj.com-home-page-20220716075018-00001.warc.gz | rg d1bxh8uas1mnw7.cloudfront.net/assets/embed.js -a -C 20

the WARC record:

    WARC/1.0
    WARC-Type: revisit
    WARC-Target-URI: https://d1bxh8uas1mnw7.cloudfront.net/assets/embed.js
    WARC-Date: 2022-07-16T08:40:26Z
    WARC-Payload-Digest: sha1:U5E5UA6DS5GGCHJ2IZSOIEGPN6P64JRB
    WARC-IP-Address: 13.227.21.220
    WARC-Profile: http://netpreserve.org/warc/1.0/revisit/identical-payload-digest
    WARC-Truncated: length
    WARC-Record-ID: <urn:uuid:cc79139e-d43f-4b43-9b9e-f923610344d0>
    Content-Type: application/http; msgtype=response
    Content-Length: 493

    HTTP/1.1 200 OK
    Content-Type: application/javascript
    Content-Length: 512
    Connection: close
    Last-Modified: Fri, 22 Apr 2022 08:45:38 GMT
    Accept-Ranges: bytes
    Server: AmazonS3
    Date: Fri, 15 Jul 2022 16:36:08 GMT
    ETag: "1c28db48d4012f0221b63224a3bb7137"
    Vary: Accept-Encoding
    X-Cache: Hit from cloudfront
    Via: 1.1 5b475307685b5cecdd0df414286f5438.cloudfront.net (CloudFront)
    X-Amz-Cf-Pop: SFO20-C1
    X-Amz-Cf-Id: SIRR_1LT8mkp3QVaiGYttPuomxyDfJ-vB6dh0Slg_qqyW0_WwnA1eg==
    Age: 57859

where are the `WARC-Refers-To-Target-URI` and `WARC-Refers-To-Date` lines?

## osf.io

    select status, terminal_status_code, count(*) from ingest_file_result where base_url LIKE 'https://doi.org/10.17605/osf.io/%' and ingest_type = 'pdf' group by status, terminal_status_code order by count(*) desc limit 30;

             status          | terminal_status_code | count
    -------------------------+----------------------+-------
     terminal-bad-status     |                  404 | 92110
     no-pdf-link             |                  200 | 46932
     not-found               |                  200 | 20212
     no-capture              |                      |  8599
     success                 |                  200 |  7604
     redirect-loop           |                  301 |  2125
     terminal-bad-status     |                  503 |  1657
     cdx-error               |                      |  1301
     wrong-mimetype          |                  200 |   901
     terminal-bad-status     |                  410 |   364
     read-timeout            |                      |   167
     wayback-error           |                      |   142
     gateway-timeout         |                      |   139
     terminal-bad-status     |                  500 |    76
     spn2-error              |                      |    63
     spn2-backoff            |                      |    42
     petabox-error           |                      |    39
     spn2-backoff            |                  200 |    27
     redirect-loop           |                  302 |    19
     terminal-bad-status     |                  400 |    15
     terminal-bad-status     |                  401 |    15
     remote-server-error     |                      |    14
     timeout                 |                      |    11
     terminal-bad-status     |                      |    11
     petabox-error           |                  200 |    10
     empty-blob              |                  200 |     8
     null-body               |                  200 |     6
     spn2-error:unknown      |                      |     5
     redirect-loop           |                  308 |     4
     spn2-cdx-lookup-failure |                      |     4
    (30 rows)

Many of these are now non-existant, or datasets/registrations not articles.
Hrm.


## Large DOAJ no-pdf-link Domains

    SELECT
        substring(ingest_file_result.terminal_url FROM '[^/]+://([^/]*)') AS domain,
        COUNT(*)
    FROM ingest_request
    LEFT JOIN ingest_file_result ON
        ingest_request.ingest_type = ingest_file_result.ingest_type
        AND ingest_request.base_url = ingest_file_result.base_url
    WHERE
        ingest_file_result.status = 'no-pdf-link'
        AND ingest_request.link_source = 'doaj'
    GROUP BY
        domain
    ORDER BY
        COUNT(*) DESC
    LIMIT 50;

                            domain                         | count  
    -------------------------------------------------------+--------
     www.sciencedirect.com                                 | 211090
     auth.openedition.org                                  |  20741
     journal.frontiersin.org:80                            |  11368
     journal.frontiersin.org                               |   6494
     ejde.math.txstate.edu                                 |   4301
     www.arkat-usa.org                                     |   4001
     www.scielo.br                                         |   3736
     www.lcgdbzz.org                                       |   2892
     revistas.uniandes.edu.co                              |   2715
     scielo.sld.cu                                         |   2612
     www.egms.de                                           |   2488
     journals.lww.com                                      |   2415
     ter-arkhiv.ru                                         |   2239
     www.kitlv-journals.nl                                 |   2076
     www.degruyter.com                                     |   2061
     jwcn-eurasipjournals.springeropen.com                 |   1929
     www.cjcnn.org                                         |   1908
     www.aimspress.com                                     |   1885
     vsp.spr-journal.ru                                    |   1873
     dx.doi.org                                            |   1648
     www.dlib.si                                           |   1582
     aprendeenlinea.udea.edu.co                            |   1548
     www.math.u-szeged.hu                                  |   1448
     dergipark.org.tr                                      |   1444
     revistas.uexternado.edu.co                            |   1429
     learning-analytics.info                               |   1419
     drive.google.com                                      |   1399
     www.scielo.cl                                         |   1326
     www.economics-ejournal.org                            |   1267
     www.jssm.org                                          |   1240
     html.rhhz.net                                         |   1232
     journalofinequalitiesandapplications.springeropen.com |   1214
     revistamedicina.net                                   |   1197
     filclass.ru                                           |   1154
     ceramicayvidrio.revistas.csic.es                      |   1152
     gynecology.orscience.ru                               |   1126
     www.tobaccoinduceddiseases.org                        |   1090
     www.tandfonline.com                                   |   1046
     www.querelles-net.de                                  |   1038
     www.swjpcc.com                                        |   1032
     microbiologyjournal.org                               |   1028
     revistas.usal.es                                      |   1027
     www.medwave.cl                                        |   1023
     ijtech.eng.ui.ac.id                                   |   1023
     www.scielo.sa.cr                                      |   1021
     vestnik.szd.si                                        |    986
     www.biomedcentral.com:80                              |    984
     scielo.isciii.es                                      |    983
     bid.ub.edu                                            |    970
     www.meirongtv.com                                     |    959
    (50 rows)

    select base_url from ingest_file_result where ingest_type = 'pdf' and status = 'no-pdf-link' and terminal_url like 'https://ejde.math.txstate.edu%' limit 5;
        http://ejde.math.txstate.edu/Volumes/2018/30/abstr.html
        http://ejde.math.txstate.edu/Volumes/2012/137/abstr.html
        http://ejde.math.txstate.edu/Volumes/2016/268/abstr.html
        http://ejde.math.txstate.edu/Volumes/2015/194/abstr.html
        http://ejde.math.txstate.edu/Volumes/2014/43/abstr.html
    # plain HTML, not really parse-able

    select base_url from ingest_file_result where ingest_type = 'pdf' and status = 'no-pdf-link' and terminal_url like 'https://www.arkat-usa.org%' limit 5;
        https://www.arkat-usa.org/arkivoc-journal/browse-arkivoc/ark.5550190.0006.913
        https://www.arkat-usa.org/arkivoc-journal/browse-arkivoc/ark.5550190.0013.909
        https://www.arkat-usa.org/arkivoc-journal/browse-arkivoc/ark.5550190.0007.717
        https://www.arkat-usa.org/arkivoc-journal/browse-arkivoc/ark.5550190.p008.158
        https://www.arkat-usa.org/arkivoc-journal/browse-arkivoc/ark.5550190.0014.216
    # fixed (embed PDF)

    select base_url from ingest_file_result where ingest_type = 'pdf' and status = 'no-pdf-link' and terminal_url like 'https://www.scielo.br%' limit 5;
        https://doi.org/10.5935/0034-7280.20200075
        https://doi.org/10.5935/0004-2749.20200071
        https://doi.org/10.5935/0034-7280.20200035
        http://www.scielo.br/scielo.php?script=sci_arttext&pid=S1516-44461999000400014
        https://doi.org/10.5935/0034-7280.20200047
    # need recrawls?
    # then success

    select base_url from ingest_file_result where ingest_type = 'pdf' and status = 'no-pdf-link' and terminal_url like 'https://www.lcgdbzz.org%' limit 5;
    select base_url from ingest_file_result where ingest_type = 'pdf' and status = 'no-pdf-link' and terminal_url like 'https://revistas.uniandes.edu.co%' limit 5;
    select base_url from ingest_file_result where ingest_type = 'pdf' and status = 'no-pdf-link' and terminal_url like 'https://scielo.sld.cu%' limit 5;
    select base_url from ingest_file_result where ingest_type = 'pdf' and status = 'no-pdf-link' and terminal_url like 'https://www.egms.de%' limit 5;
        https://doi.org/10.3205/16dgnc020
        http://nbn-resolving.de/urn:nbn:de:0183-19degam1126
        http://www.egms.de/en/meetings/dgpraec2019/19dgpraec032.shtml
        http://www.egms.de/en/meetings/dkou2019/19dkou070.shtml
        http://nbn-resolving.de/urn:nbn:de:0183-20nrwgu625
    # mostly abstracts, don't have PDF versions

    select base_url from ingest_file_result where ingest_type = 'pdf' and status = 'no-pdf-link' and terminal_url like 'https://ter-arkhiv.ru%' limit 5;
        https://doi.org/10.26442/terarkh201890114-47
        https://doi.org/10.26442/00403660.2019.12.000206
        https://journals.eco-vector.com/0040-3660/article/download/32246/pdf
        https://journals.eco-vector.com/0040-3660/article/download/33578/pdf
        https://doi.org/10.26442/00403660.2019.12.000163
    # working, needed recrawls (some force re-crawls)

    select base_url from ingest_file_result where ingest_type = 'pdf' and status = 'no-pdf-link' and terminal_url like 'https://www.kitlv-journals.nl%' limit 5;
    select base_url from ingest_file_result where ingest_type = 'pdf' and status = 'no-pdf-link' and terminal_url like 'https://www.cjcnn.org%' limit 5;


    select base_url from ingest_file_result where ingest_type = 'pdf' and status = 'no-pdf-link' and terminal_url like 'https://www.dlib.si%' limit 5;
        https://srl.si/ojs/srl/article/view/2910
        https://srl.si/ojs/srl/article/view/3640
        https://srl.si/ojs/srl/article/view/2746
        https://srl.si/ojs/srl/article/view/2557
        https://srl.si/ojs/srl/article/view/2583
    # fixed? (dlib.si)

    select base_url from ingest_file_result where ingest_type = 'pdf' and status = 'no-pdf-link' and terminal_url like 'https://www.jssm.org%' limit 5;
        http://www.jssm.org/vol4/n4/8/v4n4-8text.php
        http://www.jssm.org/vol7/n1/19/v7n1-19text.php
        http://www.jssm.org/vol9/n3/10/v9n3-10text.php
        http://www.jssm.org/abstresearcha.php?id=jssm-14-347.xml
        http://www.jssm.org/vol7/n2/11/v7n2-11text.php
    # works as an HTML document? otherwise hard to select on PDF link


    select base_url from ingest_file_result where ingest_type = 'pdf' and status = 'no-pdf-link' and terminal_url like 'https://filclass.ru%' limit 5;
        https://filclass.ru/en/archive/2018/2-52/the-chronicle-of-domestic-literary-criticism
        https://filclass.ru/en/archive/2015/42/training-as-an-effective-form-of-preparation-for-the-final-essay
        https://filclass.ru/en/archive/2020/vol-25-3/didaktizatsiya-literatury-rossijskikh-nemtsev-zanyatie-po-poeme-viktora-klyajna-jungengesprach
        https://filclass.ru/en/archive/2015/40/the-communicative-behaviour-of-the-russian-intelligentsia-and-its-reflection-in-reviews-as-a-genre-published-in-online-literary-journals-abroad
        https://filclass.ru/en/archive/2016/46/discoursive-means-of-implication-of-instructive-components-within-the-anti-utopia-genre
    # fixed
    # TODO: XXX: re-crawl/ingest

    select base_url from ingest_file_result where ingest_type = 'pdf' and status = 'no-pdf-link' and terminal_url like 'https://microbiologyjournal.org%' limit 5;
        https://microbiologyjournal.org/the-relationship-between-the-type-of-infection-and-antibiotic-resistance/
        https://microbiologyjournal.org/antimicrobial-resistant-shiga-toxin-producing-escherichia-coli-isolated-from-ready-to-eat-meat-products-and-fermented-milk-sold-in-the-formal-and-informal-sectors-in-harare-zimbabwe/
        https://microbiologyjournal.org/emerging-antibiotic-resistance-in-mycoplasma-microorganisms-designing-effective-and-novel-drugs-therapeutic-targets-current-knowledge-and-futuristic-prospects/
        https://microbiologyjournal.org/microbiological-and-physicochemicalpropertiesofraw-milkproduced-from-milking-to-delivery-to-milk-plant/
        https://microbiologyjournal.org/association-of-insulin-based-insulin-resistance-with-liver-biomarkers-in-type-2-diabetes-mellitus/
    # HTML article, no PDF
    # ... but only sometimes

    select base_url from ingest_file_result where ingest_type = 'pdf' and status = 'no-pdf-link' and terminal_url like 'https://www.medwave.cl%' limit 5;
        http://www.medwave.cl/link.cgi/Medwave/Perspectivas/Cartas/6878
        https://www.medwave.cl/link.cgi/Medwave/Revisiones/RevisionClinica/8037.act
        http://dx.doi.org/10.5867/medwave.2012.03.5332
        https://www.medwave.cl/link.cgi/Medwave/Estudios/Casos/7683.act
        http://www.medwave.cl/link.cgi/Medwave/Revisiones/CAT/5964
    # HTML article, no PDF

Re-ingest HTML:

    https://fatcat.wiki/container/mafob4ewkzczviwipyul7knndu (DONE)
    https://fatcat.wiki/container/6rgnsrp3rnexdoks3bxcmbleda (DONE)

Re-ingest PDF:

    doi_prefix:10.5935 (DONE)
    doi_prefix:10.26442

## More Scielo

More scielo?  `doi_prefix:10.5935 in_ia:false`

    http://revistaadmmade.estacio.br/index.php/reeduc/article/view/1910/47965873
    # OJS? fixed

    https://revistas.unicentro.br/index.php/repaa/article/view/2667/2240
    # working, but needed re-crawl

    http://www.rbcp.org.br/details/2804/piezoelectric-preservative-rhinoplasty--an-alternative-approach-for-treating-bifid-nose-in-tessier-no--0-facial-cleft

A few others, mostly now working

## Recent OA DOIs

    fatcat-cli search release 'is_oa:true (type:article-journal OR type:article OR type:paper-conference) !doi_prefix:10.5281 !doi_prefix:10.6084 !doi_prefix:10.48550 !doi_prefix:10.25446  !doi_prefix:10.25384 doi:* date:>2022-06-15 date:<2022-07-15 in_ia:false !publisher_type:big5' --index-json --limit 0 | pv -l > recent_missing_oa.json

    wc -l recent_missing_oa.json
    24433

    cat recent_missing_oa.json | jq .doi_prefix -r | sort | uniq -c | sort -nr | head
       4968 10.3390
       1261 10.1080
        687 10.23668
        663 10.1021
        472 10.1088
        468 10.4000
        367 10.3917
        357 10.1364
        308 10.4230
        303 10.17863

    cat recent_missing_oa.json | jq .doi_registrar -r | sort | uniq -c | sort -nr
      19496 crossref
       4836 datacite
        101 null

    cat recent_missing_oa.json | jq .publisher_type -r | sort | uniq -c | sort -nr
       9575 longtail
       8419 null
       3861 society
        822 unipress
        449 oa
        448 scielo
        430 commercial
        400 repository
         22 other
          7 archive

    cat recent_missing_oa.json | jq .publisher -r | sort | uniq -c | sort -nr | head
       4871 MDPI AG
       1107 Informa UK (Taylor & Francis)
        665 EAG-Publikationen
        631 American Chemical Society
        451 IOP Publishing
        357 The Optical Society
        347 OpenEdition
        309 CAIRN
        308 Schloss Dagstuhl - Leibniz-Zentrum für Informatik
        303 Apollo - University of Cambridge Repository

    cat recent_missing_oa.json | jq .container_name -r | sort | uniq -c | sort -nr | head
       4908 null
        378 Sustainability
        327 ACS Omega
        289 Optics Express
        271 International Journal of Environmental Research and Public Health
        270 International Journal of Health Sciences
        238 Sensors
        223 International Journal of Molecular Sciences
        207 Molecules
        193 Proceedings of the National Academy of Sciences of the United States of America

    cat recent_missing_oa.json \
        | rg -v "(MDPI|Informa UK|American Chemical Society|IOP Publishing|CAIRN|OpenEdition)" \
        | wc -l
    16558

    cat recent_missing_oa.json | rg -i mdpi | shuf -n10 | jq .doi -r
    10.3390/molecules27144419
        => was a 404
        => recrawl was successful
    10.3390/math10142398
        => was a 404
    10.3390/smartcities5030039
        => was a 404

Huh, we need to re-try/re-crawl MDPI URLs every week or so? Or special-case this situation.
Could be just a fatcat script, or a sandcrawler query.

    cat recent_missing_oa.json \
        | rg -v "(MDPI|Informa UK|American Chemical Society|IOP Publishing|CAIRN|OpenEdition)" \
        | shuf -n10 | jq .doi -r

    https://doi.org/10.18452/24860
        => success (just needed quarterly retry?)
        => b8c6c86aebd6cd2d85515441bbce052bcff033f2 (not in fatcat.wiki)
        => current status is "bad-redirect"
    https://doi.org/10.26181/20099540.v1
        => success
        => 3f9b1ff2a09f3ea9051dbbef277579e8a0b4df30
        => this is figshare, and versioned. PDF was already attached to another DOI: https://doi.org/10.26181/20099540
    https://doi.org/10.4230/lipics.sea.2022.22
        => there is a bug resulting in trailing slash in `citation_pdf_url`
        => fixed as a quirks mode
        => emailed to report
    https://doi.org/10.3897/aca.5.e89679
        => success
        => e6fd1e066c8a323dc56246631748202d5fb48808
        => current status is 'bad-redirect'
    https://doi.org/10.1103/physrevd.105.115035
        => was 404
        => success after force-recrawl of the terminal URL (not base URL)
    https://doi.org/10.1155/2022/4649660
        => was 404
        => success after force-recrawl (of base_url)
    https://doi.org/10.1090/spmj/1719
        => paywall (not actually OA)
        => https://fatcat.wiki/container/x6jfhegb3fbv3bcbqn2i3espiu is on Szczepanski list, but isn't all OA?
    https://doi.org/10.1139/as-2022-0011
        => was no-pdf-link
        => fixed fulltext URL extraction
        => still needed to re-crawl terminal PDF link? hrm
    https://doi.org/10.31703/grr.2022(vii-ii).02
        => was no-pdf-link
        => fixed! success
    https://doi.org/10.1128/spectrum.00154-22
        => was 404
        => now repeatably 503, via SPN
    https://doi.org/10.51601/ijersc.v3i3.393
        => 503 server error
    https://doi.org/10.25416/ntr.20137379.v1
        => is figshare
        => docx (not PDF)
    https://doi.org/10.25394/pgs.20263698.v1
        => figshare
        => embargo'd
    https://doi.org/10.24850/j-tyca-14-4-7
        => was no-pdf-link
        => docs.google.com/viewer (!)
        => now handle this (success)
    https://doi.org/10.26267/unipi_dione/1832
        => was bad-redirect
        => success
    https://doi.org/10.25560/98019
        => body-too-large
        => also, PDF metadata fails to parse
        => is actually like 388 MByte
    https://doi.org/10.14738/abr.106.12511
        => max-hops-exceeded
        => bumped max-hops from 6 to 8
        => then success (via google drive)
    https://doi.org/10.24350/cirm.v.19933803
        => video, not PDF
    https://doi.org/10.2140/pjm.2022.317.67
        => link-loop
        => not actually OA
    https://doi.org/10.26265/polynoe-2306
        => was bad-redirect
        => now success
    https://doi.org/10.3389/fpls.2022.826875
        => frontiers
        => was terminal-bad-status (403)
        => success on retry (not sure why)
        => maybe this is also a date-of-publication thing?
        => not sure all these should be retried though
    https://doi.org/10.14198/medcom.22240
        => was terminal-bad-status (404)
        => force-recrawl resulted in an actual landing page, but still no-pdf-link
        => but actual PDF is a real 404, it seems. oh well
    https://doi.org/10.31729/jnma.7579
        => no-capture
    https://doi.org/10.25373/ctsnet.20146931.v2
        => figshare
        => video, not document or PDF
    https://doi.org/10.1007/s42600-022-00224-0
        => not yet crawled/attempted (!)
        => springer
        => not actually OA
    https://doi.org/10.37391/ijeer.100207
        => some upstream issue (server not found)
    https://doi.org/10.1063/5.0093946
        => aip.scitation.org, is actually OA (can download in browser)
        => cookie trap?
        => redirect-loop (seems like a true redirect loop)
        => retrying the terminal PDF URL seems to have worked
    https://doi.org/10.18502/jchr.v11i2.9998
        => no actual fulltext on publisher site
    https://doi.org/10.1128/spectrum.01144-22
        => this is a 503 error, even after retrying. weird!

DONE: check `publisher_type` in chocula for:
- "MDPI AG"
- "Informa UK (Taylor & Francis)"

    cat recent_missing_oa.json | jq '[.publisher, .publisher_type]' -c | sort | uniq -c | sort -nr | head -n40
       4819 ["MDPI AG","longtail"]
        924 ["Informa UK (Taylor & Francis)",null]
        665 ["EAG-Publikationen",null]
        631 ["American Chemical Society","society"]
        449 ["IOP Publishing","society"]
        357 ["The Optical Society","society"]
        336 ["OpenEdition","oa"]
        309 ["CAIRN","repository"]
        308 ["Schloss Dagstuhl - Leibniz-Zentrum für Informatik",null]
        303 ["Apollo - University of Cambridge Repository",null]
        292 ["Springer (Biomed Central Ltd.)",null]
        275 ["Purdue University Graduate School",null]
        270 ["Suryasa and Sons","longtail"]
        257 ["La Trobe",null]
        216 ["Frontiers Media SA","longtail"]
        193 ["Proceedings of the National Academy of Sciences","society"]
        182 ["Informa UK (Taylor & Francis)","longtail"]
        176 ["American Physical Society","society"]
        168 ["Institution of Electrical Engineers","society"]
        166 ["Oxford University Press","unipress"]
        153 ["Loughborough University",null]

    chocula mostly seems to set these correctly. is the issue that the chocula
    computed values aren't coming through or getting updated? probably. both
    the release (from container) metadata update; and chocula importer not
    doing updates based on this field; and some old/incorrect values.

    did some cleanups of specific containers, and next chocula update should
    result in a bunch more `publisher_type` getting populated on older
    containers


TODO: verify URLs are actualy URLs... somewhere? in the ingest pipeline

TODO: fatcat: don't ingest figshare "work" DOIs, only the "versioned" ones (?)
    doi_prefix:10.26181

WIP: sandcrawler: regularly (weekly?) re-try 404 errors (the terminal URL, not the base url?) (or, some kind of delay?)
    doi_prefix:10.3390 (MDPI)
    doi_prefix:10.1103
    doi_prefix:10.1155

DONE: simply re-ingest all:
    doi_prefix:10.4230
        ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc280.us.archive.org,wbgrp-svc284.us.archive.org,wbgrp-svc350.us.archive.org --kafka-request-topic sandcrawler-prod.ingest-file-requests-daily --ingest-type pdf query 'doi_prefix:10.4230'
        # Counter({'ingest_request': 2096, 'elasticsearch_release': 2096, 'estimate': 2096, 'kafka': 2096})
    container_65lzi3vohrat5nnymk3dqpoycy
        ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc280.us.archive.org,wbgrp-svc284.us.archive.org,wbgrp-svc350.us.archive.org --kafka-request-topic sandcrawler-prod.ingest-file-requests-daily --ingest-type pdf container --container-id 65lzi3vohrat5nnymk3dqpoycy
        # Counter({'ingest_request': 187, 'elasticsearch_release': 187, 'estimate': 187, 'kafka': 187})
    container_5vp2bio65jdc3blx6rfhp3chde
        ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc280.us.archive.org,wbgrp-svc284.us.archive.org,wbgrp-svc350.us.archive.org --kafka-request-topic sandcrawler-prod.ingest-file-requests-daily --ingest-type pdf container --container-id 5vp2bio65jdc3blx6rfhp3chde
        # Counter({'ingest_request': 83, 'elasticsearch_release': 83, 'estimate': 83, 'kafka': 83})

DONE: verify and maybe re-ingest all:
    is_oa:true publisher:"Canadian Science Publishing" in_ia:false

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc280.us.archive.org,wbgrp-svc284.us.archive.org,wbgrp-svc350.us.archive.org --kafka-request-topic sandcrawler-prod.ingest-file-requests-daily --allow-non-oa --ingest-type pdf --force-recrawl query 'year:>2010 is_oa:true publisher:"Canadian Science Publishing" in_ia:false !journal:print'
    # Counter({'ingest_request': 1041, 'elasticsearch_release': 1041, 'estimate': 1041, 'kafka': 1041})


## Re-Ingest bad-redirect, max-hops-exceeded, and google drive

Similar to `redirect-loop`:

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_file_result.status = 'bad-redirect'
            -- AND ingest_request.ingest_type = 'pdf'
            AND (
                ingest_request.link_source = 'doi'
                OR ingest_request.link_source = 'doaj'
                OR ingest_request.link_source = 'unpaywall'
            )
    ) TO '/srv/sandcrawler/tasks/retry_badredirect.2022-07-20.rows.json';
    # COPY 100011
    # after first run: COPY 5611

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_file_result.status = 'max-hops-exceeded'
            -- AND ingest_request.ingest_type = 'pdf'
            AND (
                ingest_request.link_source = 'doi'
                OR ingest_request.link_source = 'doaj'
                OR ingest_request.link_source = 'unpaywall'
            )
    ) TO '/srv/sandcrawler/tasks/retry_maxhops.2022-07-20.rows.json';
    # COPY 3546

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_file_result.hit is false
            AND ingest_file_result.terminal_url like 'https://docs.google.com/viewer%'
            AND (
                ingest_request.link_source = 'doi'
                OR ingest_request.link_source = 'doaj'
                OR ingest_request.link_source = 'unpaywall'
            )
    ) TO '/srv/sandcrawler/tasks/retry_googledocs.2022-07-20.rows.json';
    # COPY 1082

    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/retry_badredirect.2022-07-20.rows.json > /srv/sandcrawler/tasks/retry_badredirect.2022-07-20.json
    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/retry_maxhops.2022-07-20.rows.json > /srv/sandcrawler/tasks/retry_maxhops.2022-07-20.json
    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/retry_googledocs.2022-07-20.rows.json > /srv/sandcrawler/tasks/retry_googledocs.2022-07-20.json

    cat /srv/sandcrawler/tasks/retry_badredirect.2022-07-20.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc350.us.archive.org -t sandcrawler-prod.ingest-file-requests-daily -p -1
    cat /srv/sandcrawler/tasks/retry_maxhops.2022-07-20.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc350.us.archive.org -t sandcrawler-prod.ingest-file-requests-daily -p -1
    cat /srv/sandcrawler/tasks/retry_googledocs.2022-07-20.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc350.us.archive.org -t sandcrawler-prod.ingest-file-requests-daily -p -1
    # DONE
