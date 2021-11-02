
The current sandcrawler-db crossref table was backfilled from a 2021-01
snapshot, and has not been updated since.

Would like to use the existing fatcat Kafka feed to keep the crossref table up
to date, and also backfill in GROBID reference parsing of all `unstructured`
references.

Current plan is:

1. use kafkacat CLI to dump crossref Kafka topic, from the begining of 2021 up
   to some recent date
2. use `persist_tool.py`, with a large batch size (200?) to backfill this dump
   into sandcrawler-db. this will update some rows multiple times (if there
   have been updates)
3. dump the full crossref table, as a point-in-time snapshot
4. filter to crossref records that have `unstrutured` references in them (at
   all)
5. use `grobid_tool.py` with `parallel` to batch process references
6. backfill these refs using a simple SQL COPY statement
7. deploy crossref persist worker, with ref updates on, and roll the consumer
   group back to date of dump
8. wait for everything to catch up


## Commands

Get a timestamp in milliseconds:

    2021-01-01 is:
        1609488000 in unix time (seconds)
        1609488000000 in miliseconds

Hrm, oldest messages seem to actually be from 2021-04-28T19:21:10Z though. Due
to topic compaction? Yup, we have a 180 day compaction policy on that topic,
probably from when kafka space was tight. Oh well!

Updated retention for this topic to `46656000000` (~540 days, ~18 months) using
`kafka-manager` web app.

    kafkacat -C -b wbgrp-svc263.us.archive.org -t fatcat-prod.api-crossref -o s@1609488000000 \
        | pv -l \
        | gzip \
        > crossref_feed_start20210428_end20211029.json.gz

This resulted in ~36 million rows, 46GB.

`scp` that around, then run persist on `sandcrawler-db`:

    # in pipenv, as sandcrawler user
    # manually edited to set batch size to 200
    zcat /srv/sandcrawler/tasks/crossref_feed_start20210428_end20211029.json.gz \
        | pv -l \
        | ./persist_tool.py crossref -

With a single thread, the persist process runs at about 1,000 rows/sec, which
works out to about 10 hours for 36 million rows.

At the start of this process, total PostgreSQL database size is 832.21G.

Query to dump crossref rows which have any refs and compress output with pigz:

    # dump_crossref.sql
    COPY (
        SELECT record
        FROM crossref
        WHERE record::jsonb @? '$.reference[*].unstructured'
        -- LIMIT 5
    )
    TO STDOUT
    WITH NULL '';

    # 'sed' required because of double quote escaping in postgresql output::
    # https://stackoverflow.com/questions/29869983/postgres-row-to-json-produces-invalid-json-with-double-escaped-quotes/29871069
    # 'rg' filter is just being conservative

    psql sandcrawler < dump_crossref.sql \
        | sed 's/\\"/\"/g' \
        | rg '^\{' \
        | pv -l \
        | pigz \
        > /srv/sandcrawler/tasks/crossref_sandcrawler_unstructured.json.gz


    # NOTE: -j40 is for production run with ~dedicated GROBID server with many cores
    zcat /srv/sandcrawler/tasks/crossref_sandcrawler_unstructured.json.gz \
        | parallel -j40 --linebuffer --round-robin --pipe ./grobid_tool.py --grobid-host http://wbgrp-svc096.us.archive.org:8070 parse-crossref-refs - \
        | pv -l \
        | pigz \
        > /srv/sandcrawler/tasks/crossref_sandcrawler_unstructured.grobid_refs.json.gz

    # able to do about 300-500 records/second
    # 23.9k 0:01:14 [ 320 /s]
    # 134518 total refs parsed
    # ~1817 refs/second parsed

