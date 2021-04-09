
-- Run like:
--   psql sandcrawler < dump_unextracted_pdf_petabox.sql

BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE READ ONLY DEFERRABLE;

COPY (
  SELECT DISTINCT ON (petabox.sha1hex) row_to_json(petabox)
  FROM grobid
  LEFT JOIN petabox ON grobid.sha1hex = petabox.sha1hex
  LEFT JOIN pdf_meta ON grobid.sha1hex = pdf_meta.sha1hex
  WHERE petabox.sha1hex IS NOT NULL
    AND pdf_meta.sha1hex IS NULL
)
TO '/srv/sandcrawler/tasks/dump_unextracted_pdf_petabox.2020-07-22.json'
WITH NULL '';

ROLLBACK;
