
-- Run like:
--   psql sandcrawler < dump_unextracted_pdf.sql

BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE READ ONLY DEFERRABLE;

COPY (
  SELECT DISTINCT ON (cdx.sha1hex) row_to_json(cdx)
  FROM grobid
  LEFT JOIN cdx ON grobid.sha1hex = cdx.sha1hex
  --LEFT JOIN fatcat_file ON grobid.sha1hex = fatcat_file.sha1hex
  LEFT JOIN ingest_file_result ON grobid.sha1hex = ingest_file_result.terminal_sha1hex
  LEFT JOIN pdf_meta ON grobid.sha1hex = pdf_meta.sha1hex
  WHERE cdx.sha1hex IS NOT NULL
    --AND fatcat_file.sha1hex IS NOT NULL
    AND ingest_file_result.terminal_sha1hex IS NOT NULL
    AND pdf_meta.sha1hex IS NULL
)
TO '/srv/sandcrawler/tasks/dump_unextracted_pdf.ingest.2020-10-21.json'
WITH NULL '';

ROLLBACK;
