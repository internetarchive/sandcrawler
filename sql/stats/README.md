
## SQL Table Sizes

    SELECT
        table_name,
        pg_size_pretty(table_size) AS table_size,
        pg_size_pretty(indexes_size) AS indexes_size,
        pg_size_pretty(total_size) AS total_size
      FROM (
          SELECT
              table_name,
              pg_table_size(table_name) AS table_size,
              pg_indexes_size(table_name) AS indexes_size,
              pg_total_relation_size(table_name) AS total_size
          FROM (
              SELECT ('"' || table_schema || '"."' || table_name || '"') AS table_name
              FROM information_schema.tables
              WHERE table_schema = 'public'
          ) AS all_tables
          ORDER BY total_size DESC
      ) AS pretty_sizes;


## File Metadata

Counts and total file size:

    SELECT COUNT(*) as total_count, SUM(size_bytes) as total_size FROM file_meta;

Top mimetypes:

    SELECT mimetype, COUNT(*) FROM file_meta GROUP BY mimetype ORDER BY COUNT DESC LIMIT 30;

Missing full metadata:

    SELECT COUNT(*) FROM file_meta WHERE sha256hex IS NULL;

## CDX

Total and unique-by-sha1 counts:

    SELECT COUNT(DISTINCT sha1hex) as unique_sha1, COUNT(*) as total FROM cdx;

mimetype counts:

    SELECT mimetype, COUNT(*) FROM cdx GROUP BY mimetype ORDER BY COUNT(*) DESC LIMIT 30;

## GROBID

Counts:

    SELECT COUNT(*) AS total_files FROM grobid;

Status?

    SELECT status_code, COUNT(*) FROM grobid GROUP BY status_code ORDER BY COUNT DESC LIMIT 25;

What version used?

    SELECT grobid_version, COUNT(*) FROM grobid WHERE status_code = 200 GROUP BY grobid_version ORDER BY COUNT DESC LIMIT 25;

## Petabox

Counts:

    SELECT COUNT(DISTINCT sha1hex) as unique_sha1, COUNT(*) as total FROM petabox;

## Ingests

Requests by source:

    SELECT ingest_type, link_source, COUNT(*) FROM ingest_request GROUP BY ingest_type, link_source ORDER BY COUNT DESC LIMIT 25;

    SELECT ingest_type, link_source, ingest_request_source, COUNT(*) FROM ingest_request GROUP BY ingest_type, link_source, ingest_request_source ORDER BY COUNT DESC LIMIT 35;

Uncrawled requests by source:

    # TODO: verify this?
    SELECT ingest_request.ingest_type, ingest_request.link_source, COUNT(*)
    FROM ingest_request
    LEFT JOIN ingest_file_result
        ON ingest_request.base_url = ingest_file_result.base_url
        AND ingest_request.ingest_type = ingest_file_result.ingest_type
    WHERE ingest_file_result.base_url IS NULL
    GROUP BY ingest_request.ingest_type, ingest_request.link_source ORDER BY COUNT DESC LIMIT 35;

Results by source:

    SELECT
        ingest_request.ingest_type,
        ingest_request.link_source,
        COUNT(*) as attempts,
        COUNT(CASE WHEN ingest_file_result.hit THEN 1 END) hits, 
        ROUND(1.0 * COUNT(CASE WHEN ingest_file_result.hit THEN 1 END) / COUNT(*), 3) as fraction
    FROM ingest_request
    LEFT JOIN ingest_file_result
        ON ingest_request.base_url = ingest_file_result.base_url
        AND ingest_request.ingest_type = ingest_file_result.ingest_type
        AND ingest_file_result.ingest_type IS NOT NULL
    GROUP BY ingest_request.ingest_type, ingest_request.link_source ORDER BY attempts DESC LIMIT 35;

Ingest result by status:

    SELECT ingest_type, status, COUNT(*) FROM ingest_file_result GROUP BY ingest_type, status ORDER BY COUNT DESC LIMIT 50;

Failed ingest by terminal status code:

    SELECT ingest_type, terminal_status_code, COUNT(*) FROM ingest_file_result WHERE hit = false GROUP BY ingest_type, terminal_status_code ORDER BY COUNT DESC LIMIT 50;

