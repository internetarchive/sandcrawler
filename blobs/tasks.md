
## Backfill GROBID XML to Blob Store

Initially ran this when spinning up new seaweedfs server to replace minio. At
this time grobid persist worker was in db-only mode, as minio was too slow to
accept uploads. Rough plan is to:

1. run grobid persist worker from Kafka with a new temporary consumer group,
   from the start of the GROBID output topic
2. when it gets to end, stop the *regular* consumer group while this one is
   still running. with temporary worker still running, at that point in time
   entire topic should be in S3
3. then reconfigure regular worker to db+s3 mode. halt the temporary worker,
   restart the regular one with new config, run it indefinitely

Consumer group isn't an arg, so just edit `persist_worker.py` and set it to
`persist-grobid-seaweedfs`. Also needed to patch a bit so `--s3-only` mode
didn't try to connect to postgresql.

Commands:

    ./sandcrawler_worker.py --kafka-hosts wbgrp-svc263.us.archive.org:9092 --env prod --s3-bucket sandcrawler --s3-url wbgrp-svc169.us.archive.org:8333 persist-grobid --s3-only
    => Consuming from kafka topic sandcrawler-prod.grobid-output-pg, group persist-grobid-seaweed
    => run briefly, then kill

On kafka-broker worker:

    ./kafka-consumer-groups.sh --bootstrap-server localhost:9092 --reset-offsets --to-earliest --group persist-grobid-seaweed --topic sandcrawler-prod.grobid-output-pg --dry-run

Then run 2x instances of worker (same command as above):

    ./sandcrawler_worker.py --kafka-hosts wbgrp-svc263.us.archive.org:9092 --env prod --s3-bucket sandcrawler --s3-url wbgrp-svc169.us.archive.org:8333 persist-grobid --s3-only

At this point CPU-limited on this worker by the python processes (only 4 cores
on this machine).

Check in weed shell:

    weed shell

    > > fs.meta.cat buckets/sandcrawler/grobid/00/00/000068a76ab125389506e8834483c6ba4c73338a.tei.xml
    [...]
            "isGzipped": false
    [...]
            "mime": "application/xml",
    [...]

An open question is if we should have separate buckets per derive type. Eg, a
GROBID XML bucket separate from thumbnails bucket. Or are prefix directories
enough. Basically this comes down to whether we want things mixed together at
the volume level. I think we should keep separate.

Need to set the mimetype in the upload for gzip on XML?
