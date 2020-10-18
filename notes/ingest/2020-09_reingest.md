
Goal: re-bulk-ingest some older existing crawls which hung on errors like
`cdx-error` or `wayback-error`, indicating that ingest might actually succeed
on retry.

Sources:
- unpaywall (again)
- doi (ingest, changelog, etc)
- mag
- oai

## DOI

    SELECT ingest_file_result.status, COUNT(*)
    FROM ingest_request
    LEFT JOIN ingest_file_result
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE 
        ingest_request.ingest_type = 'pdf'
        AND ingest_request.link_source = 'doi'
    GROUP BY status
    ORDER BY COUNT DESC
    LIMIT 25;

                   status                |  count  
    -------------------------------------+---------
     no-pdf-link                         | 8304582
     success                             | 3461708
     no-capture                          | 1881269
     redirect-loop                       | 1851541
     gateway-timeout                     |  355820
     cdx-error                           |  341848
     terminal-bad-status                 |  328650
     skip-url-blocklist                  |  220474
     spn2-cdx-lookup-failure             |  125521
     link-loop                           |  109352
     wayback-error                       |  101525
     null-body                           |   73539
     wrong-mimetype                      |   53151
     spn-error                           |   13579
     spn2-error                          |    6848
     spn2-error:job-failed               |    4381
     spn-remote-error                    |    4180
     other-mimetype                      |    2305
     petabox-error                       |     904
     timeout                             |     710
     spn2-error:soft-time-limit-exceeded |     557
     spn2-error:proxy-error              |     437
     spn2-error:browser-running-error    |     273
     invalid-host-resolution             |     233
     pending                             |     116
    (25 rows)

Bulk:

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'doi'
            AND (
                ingest_file_result.status = 'cdx-error' OR
                ingest_file_result.status = 'wayback-error'
            )
    ) TO '/grande/snapshots/ingest_doi_errors_2020-09-03.rows.json';
    => 443421

    ./scripts/ingestrequest_row2json.py /grande/snapshots/ingest_doi_errors_2020-09-03.rows.json | pv -l | shuf > /grande/snapshots/ingest_doi_errors_2020-09-03.requests.json

    cat /grande/snapshots/ingest_doi_errors_2020-09-03.requests.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1
    => done

Additional 27,779 success status? Hard to tell because lots of other ingest
running in parallel.

Live:

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'doi'
            AND (
                ingest_file_result.status = 'spn-error' OR
                ingest_file_result.status = 'spn2-cdx-lookup-failure' OR
                ingest_file_result.status = 'spn2-error:job-failed' OR
                ingest_file_result.status = 'spn2-error:proxy-error'
            )
    ) TO '/grande/snapshots/ingest_doi_spn_errors_2020-09-03.rows.json';
    => 143984

    ./scripts/ingestrequest_row2json.py /grande/snapshots/ingest_doi_spn_errors_2020-09-03.rows.json | pv -l | shuf > /grande/snapshots/ingest_doi_errors_2020-09-03.requests.json

    cat /grande/snapshots/ingest_doi_spn_errors_2020-09-03.requests.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests -p -1

## Unpaywall (again)

Bulk:

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND (
                ingest_file_result.status = 'cdx-error' OR
                ingest_file_result.status = 'wayback-error'
            )
    ) TO '/grande/snapshots/ingest_unpaywall_errors_2020-09-03.rows.json';
    => 43912

    ./scripts/ingestrequest_row2json.py /grande/snapshots/ingest_unpaywall_errors_2020-09-03.rows.json | pv -l | shuf > /grande/snapshots/ingest_unpaywall_errors_2020-09-03.requests.json

    cat /grande/snapshots/ingest_unpaywall_errors_2020-09-03.requests.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1
    => done

## MAG

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'mag'
            AND (
                ingest_file_result.status = 'cdx-error' OR
                ingest_file_result.status = 'wayback-error'
            )
    ) TO '/grande/snapshots/ingest_mag_errors_2020-09-03.rows.json';
    => 188175

    ./scripts/ingestrequest_row2json.py /grande/snapshots/ingest_mag_errors_2020-09-03.rows.json | pv -l | shuf > /grande/snapshots/ingest_mag_errors_2020-09-03.requests.json

    cat /grande/snapshots/ingest_mag_errors_2020-09-03.requests.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1
    => done

## OAI-PMH

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'oai'
            AND (
                ingest_file_result.status = 'cdx-error' OR
                ingest_file_result.status = 'wayback-error'
            )
    ) TO '/grande/snapshots/ingest_oai_errors_2020-09-03.rows.json';
    => 851056

    ./scripts/ingestrequest_row2json.py /grande/snapshots/ingest_oai_errors_2020-09-03.rows.json | pv -l | shuf > /grande/snapshots/ingest_oai_errors_2020-09-03.requests.json

    cat /grande/snapshots/ingest_oai_errors_2020-09-03.requests.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1
    => done

---------

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND date(ingest_request.created) > '2020-04-01'
            AND ingest_file_result.status = 'no-capture'
            AND ingest_request.base_url NOT LIKE '%journals.sagepub.com%'
            AND ingest_request.base_url NOT LIKE '%pubs.acs.org%'
            AND ingest_request.base_url NOT LIKE '%ahajournals.org%'
            AND ingest_request.base_url NOT LIKE '%www.journal.csj.jp%'
            AND ingest_request.base_url NOT LIKE '%aip.scitation.org%'
            AND ingest_request.base_url NOT LIKE '%academic.oup.com%'
            AND ingest_request.base_url NOT LIKE '%tandfonline.com%'
    ) TO '/grande/snapshots/unpaywall_nocapture_2020-05-04.rows.json';

