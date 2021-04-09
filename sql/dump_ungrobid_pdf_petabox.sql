
-- Run like:
--   psql sandcrawler < dump_ungrobid_pdf_petabox.sql

BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE READ ONLY DEFERRABLE;

COPY (
  SELECT DISTINCT ON (petabox.sha1hex) row_to_json(petabox)
  FROM petabox
  WHERE NOT EXISTS (SELECT grobid.sha1hex FROM grobid WHERE petabox.sha1hex = grobid.sha1hex AND grobid.status IS NOT NULL)
  -- uncomment/comment this to control whether only fatcat files are included
  AND EXISTS (SELECT fatcat_file.sha1hex FROM fatcat_file WHERE petabox.sha1hex = fatcat_file.sha1hex)
)
TO '/srv/sandcrawler/tasks/dump_ungrobided_pdf_petabox.2020-08-04.json'
WITH NULL '';

ROLLBACK;
