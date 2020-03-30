
## fatcat-changelog pipeline

Overall ingest status, past 3 days:

    SELECT ingest_file_result.ingest_type, ingest_file_result.status, COUNT(*)
    FROM ingest_file_result
    LEFT JOIN ingest_request
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE ingest_request.created >= NOW() - '3 day'::INTERVAL
        AND ingest_request.ingest_type = 'pdf'
        AND ingest_request.ingest_request_source = 'fatcat-changelog'
    GROUP BY ingest_file_result.ingest_type, ingest_file_result.status
    ORDER BY COUNT DESC
    LIMIT 20;

Broken domains, past 3 days:

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
            -- ingest_request.created >= NOW() - '3 day'::INTERVAL
            ingest_file_result.updated >= NOW() - '3 day'::INTERVAL
            AND ingest_request.ingest_type = 'pdf'
            AND ingest_request.ingest_request_source = 'fatcat-changelog'
    ) t1
    WHERE t1.domain != ''
        AND t1.status != 'success'
    GROUP BY domain, status
    ORDER BY COUNT DESC
    LIMIT 25;

Throughput per day, and success, for past month:

    SELECT ingest_request.ingest_type,
           date(ingest_request.created),
           COUNT(*) as total,
           COUNT(CASE ingest_file_result.status WHEN 'success' THEN 1 ELSE null END) as success
    FROM ingest_file_result
    LEFT JOIN ingest_request
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE ingest_request.created >= NOW() - '1 month'::INTERVAL
        AND ingest_request.ingest_type = 'pdf'
        AND ingest_request.ingest_request_source = 'fatcat-changelog'
    GROUP BY ingest_request.ingest_type, ingest_file_result.ingest_type, date(ingest_request.created)
    ORDER BY date(ingest_request.created) DESC;

## fatcat-ingest

Broken domains, past 7 days:

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
            -- ingest_request.created >= NOW() - '7 day'::INTERVAL
            ingest_file_result.updated >= NOW() - '24 hour'::INTERVAL
            AND ingest_request.ingest_type = 'pdf'
            AND ingest_request.ingest_request_source = 'fatcat-ingest'
    ) t1
    WHERE t1.domain != ''
        AND t1.status != 'success'
    GROUP BY domain, status
    ORDER BY COUNT DESC
    LIMIT 25;

Throughput per day, and success, for past 7 days:

    SELECT ingest_request.ingest_type,
           date(ingest_file_result.updated),
           COUNT(*) as total,
           COUNT(CASE ingest_file_result.status WHEN 'success' THEN 1 ELSE null END) as success
    FROM ingest_file_result
    LEFT JOIN ingest_request
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE
        -- ingest_request.created >= NOW() - '7 day'::INTERVAL
        ingest_file_result.updated >= NOW() - '24 hour'::INTERVAL
        AND ingest_request.ingest_type = 'pdf'
        AND ingest_request.ingest_request_source = 'fatcat-ingest'
    GROUP BY ingest_request.ingest_type, ingest_file_result.ingest_type, date(ingest_file_result.updated)
    ORDER BY date(ingest_file_result.updated) DESC;

Overall status, updated requests past 3 days:

    SELECT ingest_request.ingest_type,
           ingest_file_result.status,
           COUNT(*)
    FROM ingest_file_result
    LEFT JOIN ingest_request
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE
        -- ingest_file_result.updated >= NOW() - '3 day'::INTERVAL
        ingest_file_result.updated >= NOW() - '48 hour'::INTERVAL
        AND ingest_request.ingest_type = 'pdf'
        AND ingest_request.ingest_request_source = 'fatcat-ingest'
    GROUP BY ingest_request.ingest_type, ingest_file_result.status
    ORDER BY COUNT(*) DESC;

