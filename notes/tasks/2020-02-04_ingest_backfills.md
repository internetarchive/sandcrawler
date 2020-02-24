

## Using Fatcat Tool

Want to enqueue some backfill URLs to crawl, now that SPNv2 is on the mend.

Example dry-run:

    ./fatcat_ingest.py --dry-run --limit 50 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --after-year 2020 container --name elife

Big OA from 2020 (past month):

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --after-year 2020 container --name elife
    Will send ingest requests to kafka topic: sandcrawler-prod.ingest-file-requests
    Expecting 158 release objects in search queries
    Counter({'ingest_request': 158, 'estimate': 158, 'kafka': 158, 'elasticsearch_release': 158})

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org container --name elife
    Will send ingest requests to kafka topic: sandcrawler-prod.ingest-file-requests
    Expecting 2312 release objects in search queries
    Counter({'kafka': 2312, 'ingest_request': 2312, 'elasticsearch_release': 2312, 'estimate': 2312})

    # note: did 100 first to test
    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --after-year 2020 container --name plos
    Will send ingest requests to kafka topic: sandcrawler-prod.ingest-file-requests
    Expecting 1185 release objects in search queries
    Counter({'estimate': 1185, 'ingest_request': 1185, 'elasticsearch_release': 1185, 'kafka': 1185})

    ./fatcat_ingest.py --limit 500 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --after-year 2020 container --publisher elsevier
    Will send ingest requests to kafka topic: sandcrawler-prod.ingest-file-requests
    Expecting 89 release objects in search queries
    Counter({'elasticsearch_release': 89, 'estimate': 89, 'ingest_request': 89, 'kafka': 89})

    ./fatcat_ingest.py --limit 500 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --after-year 2020 container --publisher ieee
    Will send ingest requests to kafka topic: sandcrawler-prod.ingest-file-requests
    Expecting 499 release objects in search queries
    Counter({'kafka': 499, 'ingest_request': 499, 'estimate': 499, 'elasticsearch_release': 499})

    ./fatcat_ingest.py --limit 500 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --after-year 2020 container --name bmj
    Will send ingest requests to kafka topic: sandcrawler-prod.ingest-file-requests
    Expecting 28 release objects in search queries
    Counter({'elasticsearch_release': 28, 'ingest_request': 28, 'kafka': 28, 'estimate': 28})

    ./fatcat_ingest.py --dry-run --limit 500 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --after-year 2020 container --publisher springer
    Will send ingest requests to kafka topic: sandcrawler-prod.ingest-file-requests
    Expecting 6225 release objects in search queries
    Counter({'estimate': 6225, 'kafka': 500, 'elasticsearch_release': 500, 'ingest_request': 500})

    ./fatcat_ingest.py --limit 1000 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --allow-non-oa container --container-id zpobyv4vbranllc7oob56tgci4
    Will send ingest requests to kafka topic: sandcrawler-prod.ingest-file-requests
    Expecting 2920 release objects in search queries
    Counter({'estimate': 2920, 'elasticsearch_release': 1001, 'ingest_request': 1000, 'kafka': 1000})

Hip corona virus papers:

    ./fatcat_ingest.py --limit 2000 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --allow-non-oa query coronavirus
    Will send ingest requests to kafka topic: sandcrawler-prod.ingest-file-requests
    Expecting 5332 release objects in search queries
    Counter({'estimate': 5332, 'elasticsearch_release': 2159, 'ingest_request': 2000, 'kafka': 2000})

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --allow-non-oa query 2019-nCoV
    Will send ingest requests to kafka topic: sandcrawler-prod.ingest-file-requests
    Expecting 110 release objects in search queries
    Counter({'ingest_request': 110, 'kafka': 110, 'elasticsearch_release': 110, 'estimate': 110})

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --allow-non-oa query MERS-CoV
    Will send ingest requests to kafka topic: sandcrawler-prod.ingest-file-requests
    Expecting 589 release objects in search queries
    Counter({'estimate': 589, 'elasticsearch_release': 589, 'ingest_request': 552, 'kafka': 552})


Mixed eLife results:

    ["wrong-mimetype",null,"https://elifesciences.org/articles/54551"]
    ["success",null,"https://elifesciences.org/download/aHR0cHM6Ly9jZG4uZWxpZmVzY2llbmNlcy5vcmcvYXJ0aWNsZXMvNTE2OTEvZWxpZmUtNTE2OTEtdjEucGRm/elife-51691-v1.pdf?_hash=Jp1cLog1NzIlU%2BvjgLdbM%2BuphOwe5QWUn%2F97tbQBNG4%3D"]

## Re-Request Failed

Select some failed injest request rows to re-enqueue:

    COPY (
        SELECT row_to_json(ingest_request.*) FROM ingest_request
        LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
        WHERE ingest_request.ingest_type = 'pdf'
            AND ingest_file_result.ingest_type = 'pdf'
            AND ingest_file_result.updated < NOW() - '2 day'::INTERVAL
            AND ingest_file_result.hit = false
            AND ingest_file_result.status = 'spn2-cdx-lookup-failure'
    ) TO '/grande/snapshots/reingest_spn2cdx_20200205.rows.json';
    -- 1536 rows

Transform back to full requests:

    ./scripts/ingestrequest_row2json.py reingest_spn2cdx_20200205.rows.json > reingest_spn2cdx_20200205.json

Push into kafka (on a kafka broker node):

    cat ~/reingest_spn2cdx_20200205.json | jq . -c | kafkacat -P -b localhost -t sandcrawler-prod.ingest-file-requests -p -1

More:

    COPY (
        SELECT row_to_json(ingest_request.*) FROM ingest_request
        LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
        WHERE ingest_request.ingest_type = 'pdf'
            AND ingest_file_result.ingest_type = 'pdf'
            AND ingest_file_result.updated < NOW() - '2 day'::INTERVAL
            AND ingest_file_result.hit = false
            AND ingest_file_result.status like 'error:%'
    ) TO '/grande/snapshots/reingest_spn2err1_20200205.rows.json';
    -- COPY 1516

    COPY (
        SELECT row_to_json(ingest_request.*) FROM ingest_request
        LEFT JOIN ingest_file_result ON ingest_file_result.base_url = ingest_request.base_url
        WHERE ingest_request.ingest_type = 'pdf'
            AND ingest_file_result.ingest_type = 'pdf'
            AND ingest_file_result.updated < NOW() - '2 day'::INTERVAL
            AND ingest_file_result.hit = false
            AND ingest_file_result.status like 'spn2-error%'
    ) TO '/grande/snapshots/reingest_spn2err2_20200205.rows.json';
    -- COPY 16678

The next large ones to try would be `wayback-error` and `cdx-error`, though
these are pretty generic. Could go kafka output to try and understand those
error classes better.

Oof, as a mistake enqueued to partition 1 instead of -1 (random), so these will
take a week or more to actually process. Re-enqueued as -1; ingesting from
wayback is pretty fast, this should result mostly wayback ingests. Caught up by
end of weekend?

## Check Coverages

As follow-ups:

    elife: https://fatcat.wiki/container/en4qj5ijrbf5djxx7p5zzpjyoq/coverage
        => 2020-02-24: 7187 / 8101 = 88% preserved
    archivist: https://fatcat.wiki/container/zpobyv4vbranllc7oob56tgci4/coverage
        => 85 preserved
        => 2020-02-24: 85 / 3005 preserved (TODO)
    jcancer: https://fatcat.wiki/container/nkkzpwht7jd3zdftc6gq4eoeey/coverage
        => 2020 preserved
        => 2520 preserved
        => 2020-02-24: 2700 / 2766 preserved
    plos: https://fatcat.wiki/container/23nqq3odsjhmbi5tqavvcn7cfm/coverage
        => 2020-02-24: 7580 / 7730 = 98% preserved

