
## re-ingest some broken

    COPY (
        SELECT row_to_json(ingest_request.*) FROM ingest_request
        LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
        WHERE ingest_request.ingest_type = 'pdf'
            AND ingest_file_result.ingest_type = 'pdf'
            AND ingest_file_result.updated < NOW() - '1 hour'::INTERVAL
            AND ingest_file_result.updated > NOW() - '12 day'::INTERVAL
            AND ingest_file_result.hit = false
            AND ingest_file_result.status like 'spn2-%'
            AND ingest_file_result.status != 'spn2-error:invalid-url-syntax'
            AND ingest_file_result.status != 'spn2-error:spn2-error:filesize-limit'
    ) TO '/grande/snapshots/reingest_spn2-error_current.rows.json';

    COPY (
        SELECT row_to_json(ingest_request.*) FROM ingest_request
        LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
        WHERE ingest_request.ingest_type = 'pdf'
            AND ingest_file_result.ingest_type = 'pdf'
            AND ingest_file_result.hit = false
            AND ingest_file_result.status like 'cdx-error'
            AND ingest_file_result.updated < NOW() - '1 hour'::INTERVAL
            AND ingest_file_result.updated > NOW() - '12 day'::INTERVAL
            AND (ingest_request.ingest_request_source = 'fatcat-changelog'
                 OR ingest_request.ingest_request_source = 'fatcat-ingest')
    ) TO '/grande/snapshots/reingest_cdx-error_current.rows.json';

    COPY (
        SELECT row_to_json(ingest_request.*) FROM ingest_request
        LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
        WHERE ingest_request.ingest_type = 'pdf'
            AND ingest_file_result.ingest_type = 'pdf'
            AND ingest_file_result.hit = false
            AND ingest_file_result.status like 'cdx-error'
            AND ingest_file_result.updated < NOW() - '1 hour'::INTERVAL
            AND ingest_file_result.updated > NOW() - '12 day'::INTERVAL
            AND (ingest_request.ingest_request_source != 'fatcat-changelog'
                 AND ingest_request.ingest_request_source != 'fatcat-ingest')
    ) TO '/grande/snapshots/reingest_cdx-error_bulk_current.rows.json';

    COPY (
        SELECT row_to_json(ingest_request.*) FROM ingest_request
        LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
        WHERE ingest_request.ingest_type = 'pdf'
            AND ingest_file_result.ingest_type = 'pdf'
            AND ingest_file_result.hit = false
            AND ingest_file_result.status like 'wayback-error'
            AND ingest_file_result.updated < NOW() - '1 hour'::INTERVAL
            AND ingest_file_result.updated > NOW() - '12 day'::INTERVAL
    ) TO '/grande/snapshots/reingest_wayback-error_current.rows.json';

    COPY (
        SELECT row_to_json(ingest_request.*) FROM ingest_request
        LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
        WHERE ingest_request.ingest_type = 'pdf'
            AND ingest_file_result.ingest_type = 'pdf'
            AND ingest_file_result.hit = false
            AND ingest_file_result.status like 'gateway-timeout'
            AND ingest_file_result.updated < NOW() - '1 hour'::INTERVAL
            AND ingest_file_result.updated > NOW() - '12 day'::INTERVAL
            AND (ingest_request.ingest_request_source = 'fatcat-changelog'
                 OR ingest_request.ingest_request_source = 'fatcat-ingest')
    ) TO '/grande/snapshots/reingest_gateway-timeout.rows.json';

    COPY (
        SELECT row_to_json(ingest_request.*) FROM ingest_request
        LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
        WHERE ingest_request.ingest_type = 'pdf'
            AND ingest_file_result.ingest_type = 'pdf'
            AND ingest_file_result.hit = false
            AND ingest_file_result.status like 'petabox-error'
            AND ingest_file_result.updated < NOW() - '1 hour'::INTERVAL
            AND ingest_file_result.updated > NOW() - '12 day'::INTERVAL
            AND (ingest_request.ingest_request_source = 'fatcat-changelog'
                 OR ingest_request.ingest_request_source = 'fatcat-ingest')
    ) TO '/grande/snapshots/reingest_petabox-error_current.rows.json';

Transform:

    ./scripts/ingestrequest_row2json.py /grande/snapshots/reingest_spn2-error_current.rows.json | shuf > reingest_spn2-error_current.json
    ./scripts/ingestrequest_row2json.py /grande/snapshots/reingest_cdx-error_current.rows.json | shuf > reingest_cdx-error_current.json
    ./scripts/ingestrequest_row2json.py /grande/snapshots/reingest_cdx-error_bulk_current.rows.json | shuf > reingest_cdx-error_bulk_current.json
    ./scripts/ingestrequest_row2json.py /grande/snapshots/reingest_wayback-error_current.rows.json | shuf > reingest_wayback-error_current.json
    ./scripts/ingestrequest_row2json.py /grande/snapshots/reingest_gateway-timeout.rows.json | shuf > reingest_gateway-timeout.json
    ./scripts/ingestrequest_row2json.py /grande/snapshots/reingest_petabox-error_current.rows.json | shuf > reingest_petabox-error_current.json

Push to kafka (shuffled):

    cat reingest_spn2-error_current.json reingest_cdx-error_current.json reingest_wayback-error_current.json reingest_petabox-error_current.json | shuf | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests -p -1

    cat reingest_gateway-timeout.json | shuf | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests -p 0

    cat reingest_cdx-error_bulk_current.json | shuf | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

Push to kafka (not shuffled):

    cat reingest_spn2-error_current.json | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests -p -1
    cat reingest_cdx-error_current.json | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests -p -1
    cat reingest_cdx-error_bulk_current.json | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1
    cat reingest_wayback-error_current.json | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests -p -1
    cat reingest_gateway-timeout.json | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests -p -1
    cat reingest_petabox-error_current.json | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests -p -1

## just recent fatcat-ingest

    COPY (
        SELECT row_to_json(ingest_request.*) FROM ingest_request
        LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
        WHERE ingest_request.ingest_type = 'pdf'
            AND ingest_file_result.ingest_type = 'pdf'
            AND ingest_file_result.updated < NOW() - '1 hour'::INTERVAL
            -- AND ingest_file_result.updated > NOW() - '24 hour'::INTERVAL
            AND ingest_file_result.updated > NOW() - '7 day'::INTERVAL
            AND ingest_file_result.hit = false
            AND (ingest_file_result.status like 'spn2-%'
                 OR ingest_file_result.status like 'cdx-error'
                 OR ingest_file_result.status like 'gateway-timeout'
                 OR ingest_file_result.status like 'wayback-error'
            )
            AND ingest_file_result.status != 'spn2-error:invalid-url-syntax'
            AND ingest_file_result.status != 'spn2-error:spn2-error:filesize-limit'
            AND ingest_request.ingest_request_source = 'fatcat-ingest'
    ) TO '/grande/snapshots/reingest_fatcat_current.rows.json';

    # note: shuf
    ./scripts/ingestrequest_row2json.py /grande/snapshots/reingest_fatcat_current.rows.json | shuf > reingest_fatcat_current.json

    cat reingest_fatcat_current.json | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests -p -1

## specific domains

protocols.io:

    SELECT ingest_file_result.ingest_type, ingest_file_result.status, COUNT(*)
    FROM ingest_file_result
    LEFT JOIN ingest_request
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE ingest_request.ingest_type = 'pdf'
        AND ingest_request.base_url LIKE '%10.17504/protocols.io%'
    GROUP BY ingest_file_result.ingest_type, ingest_file_result.status
    ORDER BY COUNT DESC
    LIMIT 20;

biorxiv/medrxiv:

    SELECT ingest_file_result.ingest_type, ingest_file_result.status, COUNT(*)
    FROM ingest_file_result
    LEFT JOIN ingest_request
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE ingest_request.ingest_type = 'pdf'
        AND ingest_request.base_url LIKE '%10.1101/20%'
    GROUP BY ingest_file_result.ingest_type, ingest_file_result.status
    ORDER BY COUNT DESC
    LIMIT 20;
