
## Stats and Things

    zcat unpaywall_snapshot_2019-11-22T074546.jsonl.gz | jq .oa_locations[].url_for_pdf -r | rg -v ^null | cut -f3 -d/ | sort | uniq -c | sort -nr > top_domains.txt

## Transform

    zcat unpaywall_snapshot_2019-11-22T074546.jsonl.gz | ./unpaywall2ingestrequest.py - | pv -l > /dev/null
    => 22M 1:31:25 [   4k/s]

Shard it into batches of roughly 1 million (all are 1098096 +/- 1):

    zcat unpaywall_snapshot_2019-11-22.ingest_request.shuf.json.gz | split -n r/20 -d - unpaywall_snapshot_2019-11-22.ingest_request.split_ --additional-suffix=.json

Test ingest:

    head -n200 unpaywall_snapshot_2019-11-22.ingest_request.split_00.json | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

Add a single batch like:

    cat unpaywall_snapshot_2019-11-22.ingest_request.split_00.json | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

## Progress/Status

There are 21,961,928 lines total, in batches of 1,098,097.

    unpaywall_snapshot_2019-11-22.ingest_request.split_00.json
        => 2020-02-24 21:05 local: 1,097,523    ~22 results/sec (combined)
        => 2020-02-25 10:35 local: 0
    unpaywall_snapshot_2019-11-22.ingest_request.split_01.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_02.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_03.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_04.json
        => 2020-02-25 11:26 local: 4,388,997
        => 2020-02-25 10:14 local: 1,115,821
        => 2020-02-26 16:00 local:   265,116
    unpaywall_snapshot_2019-11-22.ingest_request.split_05.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_06.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_07.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_08.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_09.json
        => 2020-02-26 16:01 local: 6,843,708
        => 2020-02-26 16:31 local: 4,839,618
        => 2020-02-28 10:30 local: 2,619,319
    unpaywall_snapshot_2019-11-22.ingest_request.split_10.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_11.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_12.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_13.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_14.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_15.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_16.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_17.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_18.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_19.json
        => 2020-02-28 10:50 local: 13,551,887
        => 2020-03-01 23:38 local:  4,521,076
        => 2020-03-02 10:45 local:  2,827,071
        => 2020-03-02 21:06 local:  1,257,176
    added about 500k bulk re-ingest to try and work around cdx errors
        => 2020-03-02 21:30 local:  1,733,654

## Investigate Failures

Guessing than some domains are ultimately going to need direct "recrawl" via
SPNv2.

    -- top domain failures for unpaywall GWB history ingest
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
            ingest_file_result.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
    ) t1
    WHERE t1.domain != ''
        AND t1.status != 'success'
        AND t1.status != 'no-capture'
    GROUP BY domain, status
    ORDER BY COUNT DESC
    LIMIT 30;

                  domain               |       status        | count  
    -----------------------------------+---------------------+--------
     watermark.silverchair.com         | terminal-bad-status | 258432
     www.tandfonline.com               | no-pdf-link         | 203873
     journals.sagepub.com              | no-pdf-link         | 126317
     iopscience.iop.org                | terminal-bad-status | 112526
     files-journal-api.frontiersin.org | terminal-bad-status | 112499
     pubs.acs.org                      | no-pdf-link         |  94772
     www.degruyter.com                 | redirect-loop       |  89801
     www.ahajournals.org               | no-pdf-link         |  84025
     society.kisti.re.kr               | no-pdf-link         |  72849
     www.nature.com                    | redirect-loop       |  53575
     babel.hathitrust.org              | terminal-bad-status |  41063
     www.ncbi.nlm.nih.gov              | redirect-loop       |  40363
     scialert.net                      | no-pdf-link         |  38340
     www.degruyter.com                 | terminal-bad-status |  34913
     www.journal.csj.jp                | no-pdf-link         |  30881
     espace.library.uq.edu.au          | redirect-loop       |  24570
     www.jci.org                       | redirect-loop       |  24409
     aip.scitation.org                 | wrong-mimetype      |  22144
     www.vr-elibrary.de                | no-pdf-link         |  17436
     www.biorxiv.org                   | wrong-mimetype      |  15524
     ajph.aphapublications.org         | no-pdf-link         |  15083
     zookeys.pensoft.net               | redirect-loop       |  14867
     dialnet.unirioja.es               | redirect-loop       |  14486
     asa.scitation.org                 | wrong-mimetype      |  14261
     www.nrcresearchpress.com          | no-pdf-link         |  14254
     dl.acm.org                        | redirect-loop       |  14223
     osf.io                            | redirect-loop       |  14103
     www.oecd-ilibrary.org             | redirect-loop       |  12835
     journals.sagepub.com              | redirect-loop       |  12229
     iopscience.iop.org                | redirect-loop       |  11825
    (30 rows)

    -- top no-capture terminal domains
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
            ingest_file_result.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
    ) t1
    WHERE t1.domain != ''
        AND t1.status = 'no-capture'
    GROUP BY domain, status
    ORDER BY COUNT DESC
    LIMIT 30;

    => very few from any domain, interesting. Guess many of these are URLs that have truely never been crawled

    -- top no-capture base domains
    SELECT domain, status, COUNT((domain, status))
    FROM (
        SELECT
            ingest_file_result.ingest_type,
            ingest_file_result.status,
            substring(ingest_file_result.base_url FROM '[^/]+://([^/]*)') AS domain
        FROM ingest_file_result
        LEFT JOIN ingest_request
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE 
            ingest_file_result.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
    ) t1
    WHERE t1.domain != ''
        AND t1.status = 'no-capture'
    GROUP BY domain, status
    ORDER BY COUNT DESC
    LIMIT 30;

                domain            |   status   | count  
    ------------------------------+------------+--------
     academic.oup.com             | no-capture | 429888
     www.nature.com               | no-capture | 273825
     dergipark.org.tr             | no-capture | 119847
     www.biodiversitylibrary.org  | no-capture | 110220
     escholarship.org             | no-capture | 106307
     onlinelibrary.wiley.com      | no-capture |  89771
     journals.sagepub.com         | no-capture |  79297
     www.cell.com                 | no-capture |  64242
     deepblue.lib.umich.edu       | no-capture |  58080
     babel.hathitrust.org         | no-capture |  52286
     hal.archives-ouvertes.fr     | no-capture |  48549
     iopscience.iop.org           | no-capture |  42591
     dash.harvard.edu             | no-capture |  40767
     www.tandfonline.com          | no-capture |  40638
     discovery.ucl.ac.uk          | no-capture |  40633
     www.jstage.jst.go.jp         | no-capture |  39780
     www.doiserbia.nb.rs          | no-capture |  39261
     dspace.mit.edu               | no-capture |  37703
     zookeys.pensoft.net          | no-capture |  34562
     repositorio.unesp.br         | no-capture |  34437
     ashpublications.org          | no-capture |  34112
     www.cambridge.org            | no-capture |  33959
     kclpure.kcl.ac.uk            | no-capture |  31455
     society.kisti.re.kr          | no-capture |  30427
     pure.mpg.de                  | no-capture |  27650
     download.atlantis-press.com  | no-capture |  27253
     dialnet.unirioja.es          | no-capture |  26886
     link.springer.com            | no-capture |  26257
     www.valueinhealthjournal.com | no-capture |  24798
     dspace.library.uu.nl         | no-capture |  23234
    (30 rows)

    -- top no-capture base domains
    SELECT domain, status, COUNT((domain, status))
    FROM (
        SELECT
            ingest_file_result.ingest_type,
            ingest_file_result.status,
            substring(ingest_file_result.base_url FROM '[^/]+://([^/]*)') AS domain
        FROM ingest_file_result
        LEFT JOIN ingest_request
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE 
            ingest_file_result.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
    ) t1
    WHERE t1.domain != ''
        AND t1.status = 'no-capture'
    GROUP BY domain, status
    ORDER BY COUNT DESC
    LIMIT 30;

                domain            |   status   | count
    ------------------------------+------------+--------
     academic.oup.com             | no-capture | 429888
     www.nature.com               | no-capture | 273825
     dergipark.org.tr             | no-capture | 119847
     www.biodiversitylibrary.org  | no-capture | 110220
     escholarship.org             | no-capture | 106307
     onlinelibrary.wiley.com      | no-capture |  89771
     journals.sagepub.com         | no-capture |  79297
     www.cell.com                 | no-capture |  64242
     deepblue.lib.umich.edu       | no-capture |  58080
     babel.hathitrust.org         | no-capture |  52286
     hal.archives-ouvertes.fr     | no-capture |  48549
     iopscience.iop.org           | no-capture |  42591
     dash.harvard.edu             | no-capture |  40767
     www.tandfonline.com          | no-capture |  40638
     discovery.ucl.ac.uk          | no-capture |  40633
     www.jstage.jst.go.jp         | no-capture |  39780
     www.doiserbia.nb.rs          | no-capture |  39261
     dspace.mit.edu               | no-capture |  37703
     zookeys.pensoft.net          | no-capture |  34562
     repositorio.unesp.br         | no-capture |  34437
     ashpublications.org          | no-capture |  34112
     www.cambridge.org            | no-capture |  33959
     kclpure.kcl.ac.uk            | no-capture |  31455
     society.kisti.re.kr          | no-capture |  30427
     pure.mpg.de                  | no-capture |  27650
     download.atlantis-press.com  | no-capture |  27253
     dialnet.unirioja.es          | no-capture |  26886
     link.springer.com            | no-capture |  26257
     www.valueinhealthjournal.com | no-capture |  24798
     dspace.library.uu.nl         | no-capture |  23234
    (30 rows)

    -- how many ingest requests not crawled at all?
    SELECT count(*)
    FROM ingest_request
    LEFT JOIN ingest_file_result
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE
        ingest_request.ingest_type = 'pdf'
        AND ingest_request.link_source = 'unpaywall'
        AND ingest_file_result.status IS NULL;
    => 0

    -- "cookie absent" terminal pages, by domain
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
            ingest_file_result.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND ingest_file_result.terminal_url LIKE '%/cookieAbsent'
    ) t1
    WHERE t1.domain != ''
        AND t1.status != 'success'
        AND t1.status != 'no-capture'
    GROUP BY domain, status
    ORDER BY COUNT DESC
    LIMIT 30;

                 domain             |     status     | count  
    --------------------------------+----------------+--------
     journals.sagepub.com           | no-pdf-link    | 126295
     www.tandfonline.com            | no-pdf-link    | 116690
     pubs.acs.org                   | no-pdf-link    |  94619
     www.ahajournals.org            | no-pdf-link    |  84016
     www.journal.csj.jp             | no-pdf-link    |  30881
     aip.scitation.org              | wrong-mimetype |  22143
     www.vr-elibrary.de             | no-pdf-link    |  17436
     ajph.aphapublications.org      | no-pdf-link    |  15080
     asa.scitation.org              | wrong-mimetype |  14261
     www.nrcresearchpress.com       | no-pdf-link    |  14253
     journals.ametsoc.org           | no-pdf-link    |  10500
     www.journals.uchicago.edu      | no-pdf-link    |   6917
     www.icevirtuallibrary.com      | no-pdf-link    |   6484
     www.journals.uchicago.edu      | wrong-mimetype |   6191
     www.healthaffairs.org          | no-pdf-link    |   5732
     pubsonline.informs.org         | no-pdf-link    |   5672
     pinnacle-secure.allenpress.com | no-pdf-link    |   5013
     www.worldscientific.com        | no-pdf-link    |   4560
     www.ajronline.org              | wrong-mimetype |   4523
     ehp.niehs.nih.gov              | no-pdf-link    |   4514
     www.future-science.com         | no-pdf-link    |   4091
     pubs.acs.org                   | wrong-mimetype |   4015
     aip.scitation.org              | no-pdf-link    |   3916
     www.futuremedicine.com         | no-pdf-link    |   3821
     asa.scitation.org              | no-pdf-link    |   3644
     www.liebertpub.com             | no-pdf-link    |   3345
     physicstoday.scitation.org     | no-pdf-link    |   3005
     pubs.cif-ifc.org               | no-pdf-link    |   2761
     epubs.siam.org                 | wrong-mimetype |   2583
     www.ajronline.org              | no-pdf-link    |   2563
    (30 rows)

    -- "cookie absent" terminal pages, by domain
    SELECT count(*)
    FROM ingest_file_result
    LEFT JOIN ingest_request
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE 
        ingest_file_result.ingest_type = 'pdf'
        AND ingest_request.link_source = 'unpaywall'
        AND ingest_file_result.status != 'success'
        AND ingest_file_result.terminal_url LIKE '%/cookieAbsent';

    => 654885

    -- NOT "cookie absent" terminal page failures, total count
    SELECT count(*)
    FROM ingest_file_result
    LEFT JOIN ingest_request
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE 
        ingest_file_result.ingest_type = 'pdf'
        AND ingest_request.link_source = 'unpaywall'
        AND ingest_file_result.status != 'success'
        AND ingest_file_result.terminal_url NOT LIKE '%/cookieAbsent';

    => 1403837

Looks like these domains are almost all "cookieAbsent" blocking:
- journals.sagepub.com
- pubs.acs.org
- ahajournals.org
- www.journal.csj.jp
- aip.scitation.org

Grab some individual URLs to test:

    SELECT ingest_file_result.status, ingest_file_result.base_url, ingest_file_result.terminal_url
    FROM ingest_file_result
    LEFT JOIN ingest_request
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE 
        ingest_file_result.ingest_type = 'pdf'
        AND ingest_request.link_source = 'unpaywall'
        AND ingest_file_result.status != 'success'
        AND ingest_file_result.terminal_url NOT LIKE '%/cookieAbsent'
    ORDER BY updated DESC
    LIMIT 25;

NOT cookieAbsent testing with regular ingest tool:
- iopscience.iop.org, terminal-bad-status, SPNv2 fetch, success
- academic.oup.com => silverchair, terminal-bad-status, SPNv2 fetch, succes
- osf.io success

    SELECT ingest_file_result.status, ingest_file_result.base_url, ingest_file_result.terminal_url
    FROM ingest_file_result
    LEFT JOIN ingest_request
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE 
        ingest_file_result.ingest_type = 'pdf'
        AND ingest_request.link_source = 'unpaywall'
        AND ingest_file_result.status != 'success'
        AND ingest_file_result.terminal_url LIKE '%/cookieAbsent'
    ORDER BY updated DESC
    LIMIT 25;

cookieAbsent testing with regular ingest tool:
- www.tandfonline.com failure (no-pdf-link via wayback), but force-recrawl works

The main distinguisher is status. terminal-bad-status can be ingested (live)
successfully, while no-pdf-link, redirect-loop, etc need to be re-crawled.

## Heritrix Plan

Generate following ingest request batches:

- no-capture status from unpaywall
- all other failures except /cookieAbsent
- /cookieAbsent failures

Plan will be to crawl no-capture first (to completion), then try the other
non-/cookieAbsent failures. /cookieAbsent means we'll need to use SPNv2.

Because there are so few "no-capture on second hop" cases, will not enqueue
both terminal urls and base urls, only base urls.

Should definitely skip/filter:

- www.ncbi.nlm.nih.gov

## Ingest Request Export

    COPY (
        SELECT row_to_json(ingest_request.*) FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND ingest_file_result.status = 'no-capture'
    ) TO '/grande/snapshots/unpaywall_nocapture_20200304.rows.json';
    => 4,855,142

    COPY (
        SELECT row_to_json(ingest_request.*) FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND ingest_file_result.status != 'success'
            AND ingest_file_result.terminal_url NOT LIKE '%/cookieAbsent'
    ) TO '/grande/snapshots/unpaywall_fail_nocookie_20200304.rows.json';
    => 1,403,837

    ./scripts/ingestrequest_row2json.py /grande/snapshots/unpaywall_nocapture_20200304.rows.json > unpaywall_nocapture_20200304.json
    ./scripts/ingestrequest_row2json.py /grande/snapshots/unpaywall_fail_nocookie_20200304.rows.json > unpaywall_fail_nocookie_20200304.json

Note: will probably end up re-running the below after crawling+ingesting the above:

    COPY (
        SELECT row_to_json(ingest_request.*) FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND ingest_file_result.status != 'success'
            AND ingest_file_result.status = 'terminal-bad-status'
            AND ingest_file_result.terminal_url LIKE '%/cookieAbsent'
    ) TO '/grande/snapshots/unpaywall_fail_cookie_badstatus_20200304.rows.json';
    => 0

    COPY (
        SELECT row_to_json(ingest_request.*) FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND ingest_file_result.status != 'success'
            AND ingest_file_result.status != 'terminal-bad-status'
            AND ingest_file_result.terminal_url LIKE '%/cookieAbsent'
    ) TO '/grande/snapshots/unpaywall_fail_cookie_other_20200304.rows.json';
    => 654,885

## Batch Ingest

Test small batch:

    head -n200 /grande/snapshots/unpaywall_nocapture_20200304.rows.json | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

Full batch:

    cat /grande/snapshots/unpaywall_nocapture_20200304.rows.json | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

    # there was a broken line in there, so...
    # parse error: Expected separator between values at line 1367873, column 175
    # tail -n+1367875 /grande/snapshots/unpaywall_nocapture_20200304.rows.json | rg -v "\\\\" | jq . -c > /dev/null
    tail -n+1367875 /grande/snapshots/unpaywall_nocapture_20200304.rows.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

Note that the crawl is not entirely complete and not all CDX seem to have been
loaded, so may need to iterate. About 10% are still "no capture". May want or
need to additionally crawl the terminal URLs, not the base URLs.

## Post-ingest stats

Overall status:

    SELECT ingest_file_result.status, COUNT(*)
    FROM ingest_request
    LEFT JOIN ingest_file_result
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE 
        ingest_request.ingest_type = 'pdf'
        AND ingest_request.link_source = 'unpaywall'
    GROUP BY status
    ORDER BY COUNT DESC
    LIMIT 20;

             status          |  count
    -------------------------+----------
     success                 | 17354494
     no-pdf-link             |  1471076
     no-capture              |  1135992
     redirect-loop           |   837842
     terminal-bad-status     |   803081
     cdx-error               |   219746
     wrong-mimetype          |   100723
     link-loop               |    16013
     wayback-error           |    12448
     null-body               |     9444
     redirects-exceeded      |      600
     petabox-error           |      411
     bad-redirect            |       17
     bad-gzip-encoding       |        4
     spn2-cdx-lookup-failure |        3
     gateway-timeout         |        1
     spn2-error:job-failed   |        1
     spn2-error              |        1
    (18 rows)

Failures by domain:

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
            ingest_file_result.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
    ) t1
    WHERE t1.domain != ''
        AND t1.status != 'success'
        AND t1.status != 'no-capture'
    GROUP BY domain, status
    ORDER BY COUNT DESC
    LIMIT 30;

                  domain               |       status        | count
    -----------------------------------+---------------------+--------
     academic.oup.com                  | no-pdf-link         | 330211
     watermark.silverchair.com         | terminal-bad-status | 324599
     www.tandfonline.com               | no-pdf-link         | 242724
     journals.sagepub.com              | no-pdf-link         | 202050
     iopscience.iop.org                | terminal-bad-status | 144063
     files-journal-api.frontiersin.org | terminal-bad-status | 121719
     pubs.acs.org                      | no-pdf-link         | 104535
     www.ahajournals.org               | no-pdf-link         | 102653
     society.kisti.re.kr               | no-pdf-link         | 101787
     www.degruyter.com                 | redirect-loop       |  95130
     www.nature.com                    | redirect-loop       |  87534
     onlinelibrary.wiley.com           | no-pdf-link         |  84432
     www.cell.com                      | redirect-loop       |  61496
     www.degruyter.com                 | terminal-bad-status |  42919
     babel.hathitrust.org              | terminal-bad-status |  41813
     www.ncbi.nlm.nih.gov              | redirect-loop       |  40488
     scialert.net                      | no-pdf-link         |  38341
     ashpublications.org               | no-pdf-link         |  34889
     dialnet.unirioja.es               | terminal-bad-status |  32076
     www.journal.csj.jp                | no-pdf-link         |  30881
     pure.mpg.de                       | redirect-loop       |  26163
     www.jci.org                       | redirect-loop       |  24701
     espace.library.uq.edu.au          | redirect-loop       |  24591
     www.valueinhealthjournal.com      | redirect-loop       |  23740
     www.vr-elibrary.de                | no-pdf-link         |  23332
     aip.scitation.org                 | wrong-mimetype      |  22144
     osf.io                            | redirect-loop       |  18513
     www.journals.elsevier.com         | no-pdf-link         |  16710
     www.spandidos-publications.com    | redirect-loop       |  15711
     www.biorxiv.org                   | wrong-mimetype      |  15513
    (30 rows)

Dump lists for another iteration of bulk ingest:

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND ingest_file_result.status = 'no-capture'
    ) TO '/grande/snapshots/unpaywall_nocapture_20200323.rows.json';
    => 278,876

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND ingest_file_result.status != 'success'
            AND ingest_file_result.terminal_url NOT LIKE '%/cookieAbsent'
    ) TO '/grande/snapshots/unpaywall_fail_nocookie_20200323.rows.json';
    =>


    ./scripts/ingestrequest_row2json.py /grande/snapshots/unpaywall_nocapture_20200323.rows.json > unpaywall_nocapture_20200323.json

    cat unpaywall_nocapture_20200323.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

