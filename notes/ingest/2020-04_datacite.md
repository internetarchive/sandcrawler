
After the broad datacite crawl, want to ingest paper PDFs into fatcat. But many
of the DOIs are for, eg, datasets, and don't want to waste time on those.

Instead of using full ingest request file from the crawl, will generate a new
ingest request file using `fatcat_ingest.py` and set that up for bulk crawling.

## Generate Requests

    ./fatcat_ingest.py --allow-non-oa --release-types article-journal,paper-conference,article,report,thesis,book,chapter query "doi_registrar:datacite" | pv -l > /srv/fatcat/snapshots/datacite_papers_20200407.ingest_request.json
    => Expecting 8905453 release objects in search queries
    => 8.91M 11:49:50 [ 209 /s]
    => Counter({'elasticsearch_release': 8905453, 'ingest_request': 8905453, 'estimate': 8905453})

## Bulk Ingest

    cat /srv/fatcat/snapshots/datacite_papers_20200407.ingest_request.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

## Ingest Stats

Note that this will have a small fraction of non-datacite results mixed in (eg,
from COVID-19 targeted crawls):

    SELECT ingest_file_result.status, COUNT(*)
    FROM ingest_request
    LEFT JOIN ingest_file_result
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE 
        ingest_request.ingest_type = 'pdf'
        AND ingest_request.link_source = 'doi'
        AND ingest_request.ingest_type = 'pdf'
        AND ingest_request.ingest_request_source = 'fatcat-ingest'
        AND created >= '2020-04-07'
    GROUP BY status
    ORDER BY COUNT DESC
    LIMIT 20;

                   status                |  count
    -------------------------------------+---------
     no-pdf-link                         | 4646767
     redirect-loop                       | 1447229
     no-capture                          |  860235
     success                             |  849501
     terminal-bad-status                 |  174869
     cdx-error                           |  159805
     wayback-error                       |   18076
     wrong-mimetype                      |   11169
     link-loop                           |    8410
     gateway-timeout                     |    4034
     spn2-cdx-lookup-failure             |     510
     petabox-error                       |     339
     null-body                           |     251
     spn2-error                          |      19
     spn2-error:job-failed               |      14
     bad-gzip-encoding                   |      13
     timeout                             |       5
     spn2-error:soft-time-limit-exceeded |       4
     invalid-host-resolution             |       2
     spn2-error:pending                  |       1
    (20 rows)

Top domains/statuses (including success):

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
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'doi'
            AND ingest_request.ingest_type = 'pdf'
            AND ingest_request.ingest_request_source = 'fatcat-ingest'
            AND created >= '2020-04-07'
    ) t1
    WHERE t1.domain != ''
        AND t1.status != 'success'
    GROUP BY domain, status
    ORDER BY COUNT DESC
    LIMIT 30;

                    domain                 |       status        | count
    ---------------------------------------+---------------------+--------
     ssl.fao.org                           | no-pdf-link         | 862277
     www.e-periodica.ch                    | no-pdf-link         | 746781
     www.researchgate.net                  | redirect-loop       | 664524
     dlc.library.columbia.edu              | no-pdf-link         | 493111
     www.die-bonn.de                       | redirect-loop       | 352903
     figshare.com                          | no-pdf-link         | 319709
     statisticaldatasets.data-planet.com   | no-pdf-link         | 309584
     catalog.paradisec.org.au              | redirect-loop       | 225396
     zenodo.org                            | no-capture          | 193201
     digi.ub.uni-heidelberg.de             | no-pdf-link         | 184974
     open.library.ubc.ca                   | no-pdf-link         | 167841
     zenodo.org                            | no-pdf-link         | 130617
     www.google.com                        | no-pdf-link         | 111312
     www.e-manuscripta.ch                  | no-pdf-link         |  79192
     ds.iris.edu                           | no-pdf-link         |  77649
     data.inra.fr                          | no-pdf-link         |  69440
     www.tib.eu                            | no-pdf-link         |  63872
     www.egms.de                           | redirect-loop       |  53877
     archaeologydataservice.ac.uk          | redirect-loop       |  52838
     d.lib.msu.edu                         | no-pdf-link         |  45297
     www.e-rara.ch                         | no-pdf-link         |  45163
     springernature.figshare.com           | no-pdf-link         |  42527
     boris.unibe.ch                        | no-pdf-link         |  40816
     www.research-collection.ethz.ch       | no-capture          |  40350
     spectradspace.lib.imperial.ac.uk:8443 | no-pdf-link         |  33059
     repository.dri.ie                     | terminal-bad-status |  32760
     othes.univie.ac.at                    | no-pdf-link         |  32558
     repositories.lib.utexas.edu           | no-capture          |  31526
     posterng.netkey.at                    | no-pdf-link         |  30315
     zenodo.org                            | terminal-bad-status |  29614
    (30 rows)

