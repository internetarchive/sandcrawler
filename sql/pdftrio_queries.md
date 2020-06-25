
## Counts / Status

    SELECT status_code, COUNT(*) FROM pdftrio GROUP BY status_code;

    # NOTE: I earlier deleted a large fraction of non-200 status codes, so
    # these aren't representative
     status_code |  count  
    -------------+---------
              -4 |      16
              -2 |      26
             200 | 1117501
             400 |    2695
    (4 rows)


    SELECT status, COUNT(*) FROM pdftrio GROUP BY status;

        status     |  count  
    ---------------+---------
     error         |    2696
     error-connect |      26
     error-timeout |      16
     success       | 1118252
    (4 rows)

    SELECT
        COUNT(CASE WHEN ensemble_score IS NOT NULL THEN 1 ELSE NULL END) as ensemble_count,
        COUNT(CASE WHEN linear_score   IS NOT NULL THEN 1 ELSE NULL END) as linear_count,
        COUNT(CASE WHEN bert_score     IS NOT NULL THEN 1 ELSE NULL END) as bert_count,
        COUNT(CASE WHEN image_score    IS NOT NULL THEN 1 ELSE NULL END) as image_count
    FROM pdftrio;


     ensemble_count | linear_count | bert_count | image_count 
    ----------------+--------------+------------+-------------
            1120100 |       976271 |      66209 |      143829
    (1 row)

## Histograms

    SELECT width_bucket(ensemble_score * 100, 0.0, 100.0, 19) * 5 as buckets, count(*) FROM pdftrio
    WHERE status = 'success'
        AND ensemble_score IS NOT NULL
    GROUP BY buckets
    ORDER BY buckets;

    SELECT width_bucket(bert_score * 100, 0.0, 100.0, 19) * 5 as buckets, count(*) FROM pdftrio
    WHERE status = 'success'
        AND bert_score IS NOT NULL
    GROUP BY buckets
    ORDER BY buckets;

    SELECT width_bucket(linear_score * 100, 0.0, 100.0, 19) * 5 as buckets, count(*) FROM pdftrio
    WHERE status = 'success'
        AND linear_score IS NOT NULL
    GROUP BY buckets
    ORDER BY buckets;

    SELECT width_bucket(image_score * 100, 0.0, 100.0, 19) * 5 as buckets, count(*) FROM pdftrio
    WHERE status = 'success'
        AND image_score IS NOT NULL
    GROUP BY buckets
    ORDER BY buckets;

