
## fatcat-changelog pipeline

Overall ingest status, past 30 days:

    SELECT ingest_file_result.ingest_type, ingest_file_result.status, COUNT(*)
    FROM ingest_file_result
    LEFT JOIN ingest_request
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE ingest_request.created >= NOW() - '30 day'::INTERVAL
        AND ingest_request.ingest_type = 'pdf'
        AND ingest_request.ingest_request_source = 'fatcat-changelog'
    GROUP BY ingest_file_result.ingest_type, ingest_file_result.status
    ORDER BY COUNT DESC
    LIMIT 20;

Broken domains, past 30 days:

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
            ingest_file_result.updated >= NOW() - '30 day'::INTERVAL
            AND ingest_request.ingest_type = 'pdf'
            AND ingest_request.ingest_request_source = 'fatcat-changelog'
    ) t1
    WHERE t1.domain != ''
        AND t1.status != 'success'
    GROUP BY domain, status
    ORDER BY COUNT DESC
    LIMIT 25;

Summary of significant domains and status, past 7 days:

    SELECT domain, status, count
    FROM (
        SELECT domain, status, COUNT((domain, status)) as count
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
                ingest_file_result.updated >= NOW() - '7 day'::INTERVAL
                AND ingest_request.ingest_type = 'pdf'
                AND ingest_request.ingest_request_source = 'fatcat-changelog'
        ) t1
        WHERE t1.domain != ''
        GROUP BY CUBE (domain, status)
    ) t2
    WHERE count > 200
    ORDER BY domain ASC , count DESC;

Summary of DOI prefix and status, past 7 days:

    SELECT doi_prefix, status, count
    FROM (
        SELECT doi_prefix, status, COUNT((doi_prefix, status)) as count
        FROM (
            SELECT
                ingest_file_result.ingest_type,
                ingest_file_result.status,
                substring(ingest_request.link_source_id FROM '(10\.[^/]*)/.*') AS doi_prefix
            FROM ingest_file_result
            LEFT JOIN ingest_request
                ON ingest_file_result.ingest_type = ingest_request.ingest_type
                AND ingest_file_result.base_url = ingest_request.base_url
            WHERE
                ingest_file_result.updated >= NOW() - '7 day'::INTERVAL
                AND ingest_request.ingest_type = 'pdf'
                AND ingest_request.ingest_request_source = 'fatcat-changelog'
                AND ingest_request.link_source = 'doi'
        ) t1
        WHERE t1.doi_prefix != ''
        GROUP BY CUBE (doi_prefix, status)
    ) t2
    WHERE count > 200
    ORDER BY doi_prefix ASC , count DESC;


Throughput per day, and success, for past 30 days:

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

## savepapernow and fatcat-ingest recent status

Specific recent ingests (for debugging):

    -- for record layout: \x
    SELECT
        ingest_file_result.status as status,
        ingest_request.ingest_type as ingest_type,
        ingest_request.ingest_request_source as source,
        ingest_request.link_source_id as source_id,
        ingest_request.base_url as base_url,
        ingest_file_result.terminal_dt as dt,
        ingest_file_result.terminal_status_code as status_code,
        ingest_file_result.terminal_sha1hex as sha1hex,
        grobid.status as grobid_status
    FROM ingest_file_result
    LEFT JOIN ingest_request
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    LEFT JOIN grobid
        ON ingest_file_result.terminal_sha1hex = grobid.sha1hex
    WHERE
        ingest_file_result.updated >= NOW() - '24 hour'::INTERVAL
        -- AND ingest_request.ingest_type = 'pdf'
        -- AND ingest_request.ingest_type = 'html'
        AND (
            ingest_request.ingest_request_source = 'savepapernow-web'
            -- OR ingest_request.ingest_request_source = 'fatcat-ingest'
        )
    ORDER BY ingest_file_result.updated DESC
    LIMIT 100;

