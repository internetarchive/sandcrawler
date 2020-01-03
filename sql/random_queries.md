
Basic stats (2019-09-23):

    SELECT COUNT(*) FROM cdx WHERE NOT EXISTS (SELECT grobid.sha1hex FROM grobid WHERE cdx.sha1hex = grobid.sha1hex);
    => 28,023,760
    => Time: 253897.213 ms (04:13.897)

    SELECT COUNT(DISTINCT sha1hex) FROM cdx WHERE NOT EXISTS (SELECT grobid.sha1hex FROM grobid WHERE cdx.sha1hex = grobid.sha1hex);
    => 22,816,087
    => Time: 287097.944 ms (04:47.098)

    SELECT COUNT(*) FROM grobid.
    => 56,196,992

    SELECT COUNT(DISTINCT sha1hex) FROM cdx;
    => 64,348,277
    => Time: 572383.931 ms (09:32.384)

    SELECT COUNT(*) FROM cdx;
    => 74,796,777

    SELECT mimetype, COUNT(*) FROM cdx GROUP BY mimetype ORDER BY COUNT(*) DESC;
    => Time: 189067.335 ms (03:09.067)

                mimetype        |  count   
        ------------------------+----------
         application/pdf        | 51049905
         text/html              | 24841846
         text/xml               |   524682
         application/postscript |    81009
        (4 rows)

Time: 189067.335 ms (03:09.067)

    SELECT status_code, COUNT(*) FROM grobid GROUP BY status_code ORDER BY count(*) DESC;

         status_code |  count   
        -------------+----------
                 200 | 56196992

    compare with older sandcrawler/output-prod/2019-05-28-1920.35-statuscodecount:

        200     49567139
        400     3464503
        409     691917
        500     247028
        503     123

    SELECT row_to_json(cdx) FROM cdx LIMIT 5;

    SELECT row_to_json(r) FROM (
        SELECT url, datetime FROM cdx
    ) r
    LIMIT 5;

More stats (2019-12-27):

    SELECT mimetype, COUNT(*) FROM file_meta GROUP BY mimetype ORDER BY COUNT(*) DESC LIMIT 20;

    SELECT SUM(size_bytes) FROM file_meta;
