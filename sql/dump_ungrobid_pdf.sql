
-- Run like:
--   psql sandcrawler < dump_ungrobid_pdf.sql | sort -S 4G | uniq -w 40 | cut -f2 > dump_ungrobid_pdf.2019-09-23.json

BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE READ ONLY DEFERRABLE;

COPY (
    SELECT cdx.sha1hex, row_to_json(cdx) FROM cdx
    WHERE cdx.mimetype = 'application/pdf'
    AND NOT EXISTS (SELECT grobid.sha1hex FROM grobid WHERE cdx.sha1hex = grobid.sha1hex)
)
TO STDOUT
WITH NULL '';

ROLLBACK;
