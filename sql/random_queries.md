
Basic stats (2019-09-23):

    SELECT COUNT(*) FROM cdx WHERE NOT EXISTS (SELECT grobid.sha1hex FROM grobid WHERE cdx.sha1hex = grobid.sha1hex);
    => 28,023,760
    => Time: 253897.213 ms (04:13.897)

    SELECT COUNT(DISTINCT sha1hex) FROM cdx WHERE NOT EXISTS (SELECT grobid.sha1hex FROM grobid WHERE cdx.sha1hex = grobid.sha1hex);
    => 22,816,087
    => Time: 287097.944 ms (04:47.098)

    SELECT COUNT(*) FROM grobid.
    => 56,196,992

    SELECT COUNT(DISTINCT sha1hex) FROM cdx;
    => 64,348,277
    => Time: 572383.931 ms (09:32.384)

    SELECT COUNT(*) FROM cdx;
    => 74,796,777

    SELECT mimetype, COUNT(*) FROM cdx GROUP BY mimetype ORDER BY COUNT(*) DESC;
    => Time: 189067.335 ms (03:09.067)

                mimetype        |  count   
        ------------------------+----------
         application/pdf        | 51049905
         text/html              | 24841846
         text/xml               |   524682
         application/postscript |    81009
        (4 rows)

Time: 189067.335 ms (03:09.067)

    SELECT status_code, COUNT(*) FROM grobid GROUP BY status_code ORDER BY count(*) DESC;

         status_code |  count   
        -------------+----------
                 200 | 56196992

    compare with older sandcrawler/output-prod/2019-05-28-1920.35-statuscodecount:

        200     49567139
        400     3464503
        409     691917
        500     247028
        503     123

    SELECT row_to_json(cdx) FROM cdx LIMIT 5;

    SELECT row_to_json(r) FROM (
        SELECT url, datetime FROM cdx
    ) r
    LIMIT 5;

More stats (2019-12-27):

    SELECT mimetype, COUNT(*) FROM file_meta GROUP BY mimetype ORDER BY COUNT(*) DESC LIMIT 20;

    SELECT SUM(size_bytes) FROM file_meta;

"Last 24 hour progress":

    # "problem domains" and statuses
    SELECT domain, status, COUNT((domain, status))
    FROM (SELECT status, updated, substring(terminal_url FROM '[^/]+://([^/]*)') AS domain FROM ingest_file_result) t1
    WHERE t1.domain != ''
        AND t1.status != 'success'
        AND t1.updated >= NOW() - '1 day'::INTERVAL
    GROUP BY domain, status
    ORDER BY COUNT DESC
    LIMIT 10;

    # "what type of errors"
    SELECT ingest_type, status, COUNT(*)
    FROM ingest_file_result
    WHERE updated >= NOW() - '1 day'::INTERVAL
    GROUP BY ingest_type, status
    ORDER BY COUNT DESC
    LIMIT 25;

    # "throughput per day for last N days"
    SELECT ingest_type,
           date(updated),
           COUNT(*) as total,
           COUNT(CASE status WHEN 'success' THEN 1 ELSE null END) as success
    FROM ingest_file_result
    WHERE updated >= NOW() - '1 month'::INTERVAL
    GROUP BY ingest_type, date(updated)
    ORDER BY date(updated) DESC;

## Parse URLs

One approach is to do regexes, something like:

    SELECT substring(column_name FROM '[^/]+://([^/]+)/') AS domain_name FROM table_name;

Eg:

    SELECT DISTINCT(domain), COUNT(domain)
        FROM (select substring(base_url FROM '[^/]+://([^/]*)') as domain FROM ingest_file_result) t1
        WHERE t1.domain != ''
        GROUP BY domain
        ORDER BY COUNT DESC 
        LIMIT 10;

Or:

    SELECT domain, status, COUNT((domain, status))
        FROM (SELECT status, substring(terminal_url FROM '[^/]+://([^/]*)') AS domain FROM ingest_file_result) t1
        WHERE t1.domain != ''
            AND t1.status != 'success'
        GROUP BY domain, status
        ORDER BY COUNT DESC
        LIMIT 10;

Can also do some quick lookups for a specific domain and protocol like:

    SELECT *
        FROM ingest_file_result
        WHERE terminal_url LIKE 'https://insights.ovid.com/%'
        LIMIT 10;

## Bulk Ingest

Show bulk ingest status on links *added* in the past week:

    SELECT ingest_file_result.ingest_type, ingest_file_result.status, COUNT(*)
    FROM ingest_file_result
    LEFT JOIN ingest_request
        ON ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    WHERE ingest_request.created >= NOW() - '30 day'::INTERVAL
        AND ingest_request.link_source = 'unpaywall'
    GROUP BY ingest_file_result.ingest_type, ingest_file_result.status
    ORDER BY COUNT DESC
    LIMIT 25;

Top *successful* domains:

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
        WHERE ingest_request.created >= NOW() - '7 day'::INTERVAL
            AND ingest_request.link_source = 'unpaywall'
    ) t1
    WHERE t1.domain != ''
        AND t1.status = 'success'
    GROUP BY domain, status
    ORDER BY COUNT DESC
    LIMIT 20;

Summarize non-success domains for the same:

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
        WHERE ingest_request.created >= NOW() - '7 day'::INTERVAL
            AND ingest_request.link_source = 'unpaywall'
    ) t1
    WHERE t1.domain != ''
        AND t1.status != 'success'
    GROUP BY domain, status
    ORDER BY COUNT DESC
    LIMIT 20;
