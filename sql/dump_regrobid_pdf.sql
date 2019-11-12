
-- Run like:
--   psql sandcrawler < dump_regrobid_pdf.sql | sort -S 4G | uniq -w 40 | cut -f2 > dump_regrobid_pdf.2019-11-12.json

BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE READ ONLY DEFERRABLE;

COPY (
    SELECT cdx.sha1hex, row_to_json(cdx) FROM cdx
    WHERE cdx.mimetype = 'application/pdf'
    AND EXISTS (SELECT grobid.sha1hex FROM grobid WHERE cdx.sha1hex = grobid.sha1hex AND grobid.grobid_version IS NULL)
)
TO STDOUT
WITH NULL '';

ROLLBACK;
