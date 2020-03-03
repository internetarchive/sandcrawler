
## Stats and Things

    zcat unpaywall_snapshot_2019-11-22T074546.jsonl.gz | jq .oa_locations[].url_for_pdf -r | rg -v ^null | cut -f3 -d/ | sort | uniq -c | sort -nr > top_domains.txt

## Transform

    zcat unpaywall_snapshot_2019-11-22T074546.jsonl.gz | ./unpaywall2ingestrequest.py - | pv -l > /dev/null
    => 22M 1:31:25 [   4k/s]

Shard it into batches of roughly 1 million (all are 1098096 +/- 1):

    zcat unpaywall_snapshot_2019-11-22.ingest_request.shuf.json.gz | split -n r/20 -d - unpaywall_snapshot_2019-11-22.ingest_request.split_ --additional-suffix=.json

Test ingest:

    head -n200 unpaywall_snapshot_2019-11-22.ingest_request.split_00.json | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

Add a single batch like:

    cat unpaywall_snapshot_2019-11-22.ingest_request.split_00.json | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

## Progress/Status

There are 21,961,928 lines total, in batches of 1,098,097.

    unpaywall_snapshot_2019-11-22.ingest_request.split_00.json
        => 2020-02-24 21:05 local: 1,097,523    ~22 results/sec (combined)
        => 2020-02-25 10:35 local: 0
    unpaywall_snapshot_2019-11-22.ingest_request.split_01.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_02.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_03.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_04.json
        => 2020-02-25 11:26 local: 4,388,997
        => 2020-02-25 10:14 local: 1,115,821
        => 2020-02-26 16:00 local:   265,116
    unpaywall_snapshot_2019-11-22.ingest_request.split_05.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_06.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_07.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_08.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_09.json
        => 2020-02-26 16:01 local: 6,843,708
        => 2020-02-26 16:31 local: 4,839,618
        => 2020-02-28 10:30 local: 2,619,319
    unpaywall_snapshot_2019-11-22.ingest_request.split_10.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_11.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_12.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_13.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_14.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_15.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_16.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_17.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_18.json
    unpaywall_snapshot_2019-11-22.ingest_request.split_19.json
        => 2020-02-28 10:50 local: 13,551,887
        => 2020-03-01 23:38 local:  4,521,076
        => 2020-03-02 10:45 local:  2,827,071
        => 2020-03-02 21:06 local:  1,257,176
    added about 500k bulk re-ingest to try and work around cdx errors
        => 2020-03-02 21:30 local:  1,733,654
