
-- Run like:
--   psql sandcrawler < dump_ungrobid_pdf.sql

BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE READ ONLY DEFERRABLE;

COPY (
  SELECT DISTINCT ON (cdx.sha1hex) row_to_json(cdx)
  FROM cdx
  WHERE cdx.mimetype = 'application/pdf'
  AND NOT EXISTS (SELECT grobid.sha1hex FROM grobid WHERE cdx.sha1hex = grobid.sha1hex AND grobid.status IS NOT NULL)
  -- uncomment/comment this to control whether only fatcat files are included
  --AND EXISTS (SELECT fatcat_file.sha1hex FROM fatcat_file WHERE cdx.sha1hex = fatcat_file.sha1hex)
)
TO '/grande/snapshots/dump_ungrobided_pdf.fatcat.2020-08-04.json'
WITH NULL '';

ROLLBACK;
