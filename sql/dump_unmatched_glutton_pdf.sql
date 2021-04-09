
-- Run like:
--   psql sandcrawler < THING.sql > THING.2019-09-23.json

BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE READ ONLY DEFERRABLE;

COPY (
  SELECT row_to_json(grobid)
  FROM grobid
  LEFT JOIN fatcat_file ON grobid.sha1hex = fatcat_file.sha1hex
  WHERE fatcat_file.sha1hex IS NULL
  AND grobid.fatcat_release IS NOT NULL
  LIMIT 1000
)
TO '/srv/sandcrawler/tasks/dump_unmatched_glutton_pdf.2020-06-30.json';
--TO STDOUT
--WITH NULL '';

ROLLBACK;
