
New snapshot released 2020-10-09. Want to do a mostly straight-forward
load/ingest/crawl.

Proposed changes this time around:

- have bulk ingest store missing URLs in a new sandcrawler-db for `no-capture`
  status, and to include those URLs in heritrix3 crawl
- tweak heritrix3 config for additional PDF URL extraction patterns,
  particularly to improve OJS yield


## Transform and Load

    # in sandcrawler pipenv on aitio
    zcat /schnell/unpaywall/unpaywall_snapshot_2020-10-09T153852.jsonl.gz | ./scripts/unpaywall2ingestrequest.py - | pv -l > /grande/snapshots/unpaywall_snapshot_2020-10-09.ingest_request.json
    => 28.3M 3:19:03 [2.37k/s]

    cat /grande/snapshots/unpaywall_snapshot_2020-04-27.ingest_request.json | pv -l | ./persist_tool.py ingest-request -
    => 28.3M 1:11:29 [ 6.6k/s]
    => Worker: Counter({'total': 28298500, 'insert-requests': 4119939, 'update-requests': 0})
    => JSON lines pushed: Counter({'total': 28298500, 'pushed': 28298500})

## Dump new URLs, Transform, Bulk Ingest

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            -- AND date(ingest_request.created) > '2020-10-09'
            AND (ingest_file_result.status IS NULL
                OR ingest_file_result.status = 'no-capture')
    ) TO '/grande/snapshots/unpaywall_noingest_2020-10-09.rows.json';

    ./scripts/ingestrequest_row2json.py /grande/snapshots/unpaywall_noingest_2020-10-09.rows.json | pv -l | shuf > /grande/snapshots/unpaywall_noingest_2020-10-09.ingest_request.json


