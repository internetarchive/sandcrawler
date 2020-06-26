
-- Run like:
--   psql sandcrawler < dump_unextracted_pdf.sql > dump_unextracted_pdf.2019-09-23.json

BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE READ ONLY DEFERRABLE;

COPY (
  SELECT row_to_json(cdx)
  FROM grobid
  LEFT JOIN cdx ON grobid.sha1hex = cdx.sha1hex
  --LEFT JOIN fatcat_file ON grobid.sha1hex = fatcat_file.sha1hex
  WHERE cdx.sha1hex IS NOT NULL
  --AND fatcat_file.sha1hex IS NOT NULL
)
--TO '/grande/snapshots/dump_unextracted_pdf.2020-06-25.json';
TO STDOUT
WITH NULL '';

ROLLBACK;
