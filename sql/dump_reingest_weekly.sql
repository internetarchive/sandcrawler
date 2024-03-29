
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE READ ONLY DEFERRABLE;

COPY (
    SELECT row_to_json(ingest_request.*) FROM ingest_request
    LEFT JOIN ingest_file_result ON
        ingest_file_result.base_url = ingest_request.base_url
        AND ingest_file_result.ingest_type = ingest_request.ingest_type
    WHERE
        (ingest_request.ingest_type = 'pdf'
            OR ingest_request.ingest_type = 'html'
            OR ingest_request.ingest_type = 'xml'
            OR ingest_request.ingest_type = 'component')
        AND ingest_file_result.hit = false
        AND ingest_request.created < NOW() - '8 hour'::INTERVAL
        AND ingest_request.created > NOW() - '8 day'::INTERVAL
        AND (ingest_request.ingest_request_source = 'fatcat-changelog'
             OR ingest_request.ingest_request_source = 'fatcat-ingest'
             OR ingest_request.ingest_request_source = 'fatcat-ingest-container')
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
) TO '/srv/sandcrawler/tasks/reingest_weekly_current.rows.json';

-- bulk re-tries would be:
--      AND (ingest_request.ingest_request_source != 'fatcat-changelog'
--           AND ingest_request.ingest_request_source != 'fatcat-ingest')

ROLLBACK;
