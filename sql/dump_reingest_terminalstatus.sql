
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE READ ONLY DEFERRABLE;

COPY (
    SELECT row_to_json(ingest_request.*) FROM ingest_request
    LEFT JOIN ingest_file_result ON
        ingest_file_result.base_url = ingest_request.base_url
        AND ingest_file_result.ingest_type = ingest_request.ingest_type
    WHERE
        ingest_file_result.hit = false
        AND ingest_request.created < NOW() - '72 hour'::INTERVAL
        AND ingest_request.created > NOW() - '10 day'::INTERVAL
        AND (ingest_request.ingest_request_source = 'fatcat-changelog'
             OR ingest_request.ingest_request_source = 'fatcat-ingest')
        AND ingest_file_result.status = 'terminal-bad-status'
        AND (
             ingest_file_result.terminal_status_code = 500
             OR ingest_file_result.terminal_status_code = 502
             OR ingest_file_result.terminal_status_code = 503
             OR ingest_file_result.terminal_status_code = 429
             OR ingest_file_result.terminal_status_code = 404
        )
	AND (
		ingest_request.base_url LIKE 'https://doi.org/10.3390/%'
		OR ingest_request.base_url LIKE 'https://doi.org/10.1103/%'
		OR ingest_request.base_url LIKE 'https://doi.org/10.1155/%'
	)
) TO '/srv/sandcrawler/tasks/reingest_terminalstatus_current.rows.json';

-- bulk re-tries would be:
--      AND (ingest_request.ingest_request_source != 'fatcat-changelog'
--           AND ingest_request.ingest_request_source != 'fatcat-ingest')

ROLLBACK;
