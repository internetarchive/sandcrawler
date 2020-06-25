
Accidentally seem to have backfilled many CDX lines with non-PDF content.
Should clear these out!

Something like:

    mimetype = 'text/html'
    not in file_meta

Or maybe instead:

    mimetype = 'text/html'
    not in file_meta

SQL:

    SELECT *        FROM cdx WHERE mimetype = 'text/html' AND row_created < '2019-10-01' LIMIT 5;
    SELECT COUNT(1) FROM cdx WHERE mimetype = 'text/html' AND row_created < '2019-10-01';
    => 24841846

    SELECT *        FROM cdx LEFT JOIN file_meta ON file_meta.sha1hex = cdx.sha1hex WHERE cdx.mimetype = 'text/html' AND file_meta.sha256hex IS NULL LIMIT 5;
    SELECT COUNT(1) FROM cdx LEFT JOIN file_meta ON cdx.sha1hex = file_meta.sha1hex WHERE cdx.mimetype = 'text/html' AND file_meta.sha256hex IS NULL;
    => 24547552

    DELETE FROM cdx
      WHERE sha1hex IN
      (SELECT cdx.sha1hex
       FROM cdx
       LEFT JOIN file_meta ON file_meta.sha1hex = cdx.sha1hex
       WHERE cdx.mimetype = 'text/html' AND file_meta.sha256hex IS NULL);
    => DELETE 24553428

Slightly more... probably should have had a "AND cdx.mimetype = 'text/html'" in
the DELETE WHERE clause.
