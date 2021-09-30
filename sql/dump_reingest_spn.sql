
COPY (
    SELECT row_to_json(ingest_request.*) FROM ingest_request
    LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
    WHERE ingest_request.ingest_type = 'pdf'
        AND ingest_file_result.hit = false
        AND ingest_request.created < NOW() - '2 hour'::INTERVAL
        AND ingest_request.created > NOW() - '31 day'::INTERVAL
        AND ingest_request.ingest_request_source = 'savepapernow-web'
        AND (
            ingest_file_result.status like 'spn2-%'
            -- OR ingest_file_result.status like 'cdx-error'
            -- OR ingest_file_result.status like 'wayback-error'
            -- OR ingest_file_result.status like 'wayback-content-error'
            OR ingest_file_result.status like 'petabox-error'
            -- OR ingest_file_result.status like 'gateway-timeout'
        )
        AND ingest_file_result.status != 'spn2-error:invalid-url-syntax'
        AND ingest_file_result.status != 'spn2-error:filesize-limit'
        AND ingest_file_result.status != 'spn2-error:not-found'
        AND ingest_file_result.status != 'spn2-error:blocked-url'
        AND ingest_file_result.status != 'spn2-error:too-many-redirects'
        AND ingest_file_result.status != 'spn2-error:network-authentication-required'
        AND ingest_file_result.status != 'spn2-error:unknown'
) TO '/srv/sandcrawler/tasks/reingest_spn.rows.json';
