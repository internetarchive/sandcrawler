
-- Run like:
--   psql sandcrawler < dump_regrobid_pdf_petabox.sql
--   cat dump_regrobid_pdf_petabox.2020-02-03.json | sort -S 4G | uniq -w 40 | cut -f2 > dump_regrobid_pdf_petabox.2020-02-03.uniq.json

BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE READ ONLY DEFERRABLE;

COPY (
    SELECT petabox.sha1hex, row_to_json(petabox) FROM petabox
    WHERE EXISTS (SELECT grobid.sha1hex FROM grobid WHERE petabox.sha1hex = grobid.sha1hex AND grobid.grobid_version IS NULL)
)
TO '/srv/sandcrawler/tasks/dump_regrobid_pdf_petabox.2020-02-03.json'
WITH NULL '';

ROLLBACK;
