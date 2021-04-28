
COPY (
    SELECT row_to_json(ingest_request.*) FROM ingest_request
    LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
    WHERE ingest_request.ingest_type = 'pdf'
        AND ingest_file_result.ingest_type = 'pdf'
        AND ingest_request.created < NOW() - '8 hour'::INTERVAL
        AND ingest_request.created > NOW() - '8 day'::INTERVAL
        AND ingest_file_result.hit = false
        AND ingest_file_result.status like 'spn2-%'
        AND ingest_file_result.status != 'spn2-error:invalid-url-syntax'
        AND ingest_file_result.status != 'spn2-error:filesize-limit'
        AND ingest_file_result.status != 'spn2-error:not-found'
        AND ingest_file_result.status != 'spn2-error:blocked-url'
        AND ingest_file_result.status != 'spn2-error:too-many-redirects'
        AND ingest_file_result.status != 'spn2-error:network-authentication-required'
) TO '/srv/sandcrawler/tasks/reingest_weekly_spn2-error_current.rows.json';

COPY (
    SELECT row_to_json(ingest_request.*) FROM ingest_request
    LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
    WHERE ingest_request.ingest_type = 'pdf'
        AND ingest_file_result.ingest_type = 'pdf'
        AND ingest_file_result.hit = false
        AND ingest_file_result.status like 'cdx-error'
        AND ingest_request.created < NOW() - '8 hour'::INTERVAL
        AND ingest_request.created > NOW() - '8 day'::INTERVAL
        AND (ingest_request.ingest_request_source = 'fatcat-changelog'
             OR ingest_request.ingest_request_source = 'fatcat-ingest')
) TO '/srv/sandcrawler/tasks/reingest_weekly_cdx-error_current.rows.json';

COPY (
    SELECT row_to_json(ingest_request.*) FROM ingest_request
    LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
    WHERE ingest_request.ingest_type = 'pdf'
        AND ingest_file_result.ingest_type = 'pdf'
        AND ingest_file_result.hit = false
        AND ingest_file_result.status like 'cdx-error'
        AND ingest_request.created < NOW() - '8 hour'::INTERVAL
        AND ingest_request.created > NOW() - '8 day'::INTERVAL
        AND (ingest_request.ingest_request_source != 'fatcat-changelog'
             AND ingest_request.ingest_request_source != 'fatcat-ingest')
) TO '/srv/sandcrawler/tasks/reingest_weekly_cdx-error_bulk_current.rows.json';

COPY (
    SELECT row_to_json(ingest_request.*) FROM ingest_request
    LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
    WHERE ingest_request.ingest_type = 'pdf'
        AND ingest_file_result.ingest_type = 'pdf'
        AND ingest_file_result.hit = false
        AND ingest_file_result.status like 'wayback-error'
        AND ingest_request.created < NOW() - '8 hour'::INTERVAL
        AND ingest_request.created > NOW() - '8 day'::INTERVAL
) TO '/srv/sandcrawler/tasks/reingest_weekly_wayback-error_current.rows.json';

COPY (
    SELECT row_to_json(ingest_request.*) FROM ingest_request
    LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
    WHERE ingest_request.ingest_type = 'pdf'
        AND ingest_file_result.ingest_type = 'pdf'
        AND ingest_file_result.hit = false
        AND ingest_file_result.status like 'gateway-timeout'
        AND ingest_request.created < NOW() - '8 hour'::INTERVAL
        AND ingest_request.created > NOW() - '8 day'::INTERVAL
        AND (ingest_request.ingest_request_source = 'fatcat-changelog'
             OR ingest_request.ingest_request_source = 'fatcat-ingest')
) TO '/srv/sandcrawler/tasks/reingest_weekly_gateway-timeout.rows.json';

COPY (
    SELECT row_to_json(ingest_request.*) FROM ingest_request
    LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
    WHERE ingest_request.ingest_type = 'pdf'
        AND ingest_file_result.ingest_type = 'pdf'
        AND ingest_file_result.hit = false
        AND ingest_file_result.status like 'petabox-error'
        AND ingest_request.created < NOW() - '8 hour'::INTERVAL
        AND ingest_request.created > NOW() - '8 day'::INTERVAL
        AND (ingest_request.ingest_request_source = 'fatcat-changelog'
             OR ingest_request.ingest_request_source = 'fatcat-ingest')
) TO '/srv/sandcrawler/tasks/reingest_weekly_petabox-error_current.rows.json';

