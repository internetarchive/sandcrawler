
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE READ ONLY DEFERRABLE;

COPY (
    SELECT row_to_json(ingest_request.*) FROM ingest_request
    LEFT JOIN ingest_file_result ON
        ingest_file_result.base_url = ingest_request.base_url
        AND ingest_file_result.ingest_type = ingest_request.ingest_type
    WHERE
        (ingest_request.ingest_type = 'pdf'
            OR ingest_request.ingest_type = 'html')
        AND ingest_file_result.hit = false
        AND ingest_request.created < NOW() - '6 hour'::INTERVAL
        AND ingest_request.created > NOW() - '180 day'::INTERVAL
        AND ingest_request.ingest_request_source = 'savepapernow-web'
        AND (
            ingest_file_result.status like 'spn2-%'
            -- OR ingest_file_result.status = 'cdx-error'
            -- OR ingest_file_result.status = 'wayback-error'
            -- OR ingest_file_result.status = 'wayback-content-error'
            OR ingest_file_result.status = 'petabox-error'
            -- OR ingest_file_result.status = 'gateway-timeout'
            OR ingest_file_result.status = 'no-capture'
        )
        AND ingest_file_result.status != 'spn2-error:invalid-url-syntax'
        AND ingest_file_result.status != 'spn2-error:filesize-limit'
        AND ingest_file_result.status != 'spn2-error:not-found'
        AND ingest_file_result.status != 'spn2-error:blocked-url'
        AND ingest_file_result.status != 'spn2-error:too-many-redirects'
        AND ingest_file_result.status != 'spn2-error:network-authentication-required'
        AND ingest_file_result.status != 'spn2-error:unknown'
) TO '/srv/sandcrawler/tasks/reingest_spn.rows.json';

ROLLBACK;
