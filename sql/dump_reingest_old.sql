
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE READ ONLY DEFERRABLE;

COPY (
    SELECT row_to_json(ingest_request.*) FROM ingest_request
    LEFT JOIN ingest_file_result ON
        ingest_file_result.base_url = ingest_request.base_url
        AND ingest_file_result.ingest_type = ingest_request.ingest_type
    WHERE
        ingest_file_result.hit = false
        AND ingest_request.created < NOW() - '6 day'::INTERVAL
        -- AND ingest_request.created > NOW() - '181 day'::INTERVAL
        AND (ingest_request.ingest_request_source = 'fatcat-changelog'
             OR ingest_request.ingest_request_source = 'fatcat-ingest'
             OR ingest_request.ingest_request_source = 'fatcat-ingest-container'
             OR ingest_request.ingest_request_source = 'unpaywall'
             OR ingest_request.ingest_request_source = 'arxiv'
             OR ingest_request.ingest_request_source = 'pmc'
             OR ingest_request.ingest_request_source = 'doaj'
             OR ingest_request.ingest_request_source = 'dblp')
        AND (
            ingest_file_result.status like 'spn2-%'
            -- OR ingest_file_result.status like 'no-capture'
            -- OR ingest_file_result.status like 'cdx-error'
            -- OR ingest_file_result.status like 'petabox-error'
        )
        AND ingest_file_result.status != 'spn2-error:invalid-url-syntax'
        AND ingest_file_result.status != 'spn2-error:filesize-limit'
        AND ingest_file_result.status != 'spn2-error:not-found'
        AND ingest_file_result.status != 'spn2-error:blocked-url'
        AND ingest_file_result.status != 'spn2-error:too-many-redirects'
        AND ingest_file_result.status != 'spn2-error:network-authentication-required'
        AND ingest_file_result.status != 'spn2-error:unknown'
) TO '/srv/sandcrawler/tasks/reingest_old_current.rows.json';

ROLLBACK;
