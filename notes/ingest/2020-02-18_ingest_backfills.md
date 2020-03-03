
Select:

    COPY (
        SELECT row_to_json(ingest_request.*) FROM ingest_request
        LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
        WHERE ingest_request.ingest_type = 'pdf'
            AND ingest_file_result.ingest_type = 'pdf'
            AND ingest_file_result.updated < NOW() - '2 day'::INTERVAL
            AND ingest_file_result.hit = false
            AND ingest_file_result.status like 'spn2-error%'
    ) TO '/grande/snapshots/reingest_spn2err_20200218.rows.json';
    => COPY 6537

    COPY (
        SELECT row_to_json(ingest_request.*) FROM ingest_request
        LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
        WHERE ingest_request.ingest_type = 'pdf'
            AND ingest_file_result.ingest_type = 'pdf'
            AND ingest_file_result.hit = false
            AND ingest_file_result.status like 'wayback-error'
    ) TO '/grande/snapshots/reingest_waybackerr_20200218.rows.json';
    => COPY 33022

Transform:

    ./scripts/ingestrequest_row2json.py reingest_spn2err_20200218.rows.json > reingest_spn2err_20200218.json
    ./scripts/ingestrequest_row2json.py reingest_waybackerr_20200218.rows.json > reingest_waybackerr_20200218.json

Push to kafka:

    cat reingest_spn2err_20200218.json | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests -p -1
    cat reingest_waybackerr_20200218.json | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests -p -1

Many had null `ingest_request_source`, so won't actually import into fatcat:

    bnewbold@ia601101$ cat reingest_waybackerr_20200218.json | jq .ingest_request_source | sort | uniq -c | sort -n
          1 "savepapernow-web"
        112 "fatcat-ingest-container"
      11750 "fatcat-changelog"
      21159 null

