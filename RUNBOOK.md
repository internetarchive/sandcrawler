
## Process Un-GROBID-ed PDFs from Wayback

Sometimes ingest doesn't pick up everything, or we do some heuristic CDX
import, and we want to run GROBID over all the PDFs that haven't been processed
yet. Only want one CDX line per `sha1hex`.

A hybrid SQL/UNIX way of generating processing list:

    psql sandcrawler < /fast/sandcrawler/sql/dump_ungrobid_pdf.sql | sort -S 4G | uniq -w 40 | cut -f2 > dump_ungrobid_pdf.2020.01-27.json

From here, there are two options: enqueue in Kafka and let workers run, or
create job files and run them using local worker and GNU/parallel.

#### Kafka

Copy/transfer to a Kafka node; load a sample and then the whole output:

    head -n1000 dump_ungrobid_pdf.2020.01-27.json | kafkacat -P -b localhost -t sandcrawler-prod.ungrobided-pg -p -1
    cat dump_ungrobid_pdf.2020.01-27.json | kafkacat -P -b localhost -t sandcrawler-prod.ungrobided-pg -p -1

#### Local JSON

Older example; if this fails, need to re-run entire thing:

    cat /srv/sandcrawler/tasks/regrobid_cdx.split_*.json | pv -l | parallel -j40 --linebuffer --round-robin --pipe ./grobid_tool.py --kafka-env prod --kafka-hosts wbgrp-svc350.us.archive.org:9092,wbgrp-svc284.us.archive.org:9092,wbgrp-svc285.us.archive.org:9092 --kafka-mode --grobid-host http://localhost:8070 -j0 extract-json -

TODO: is it possible to use job log with millions of `--pipe` inputs? That
would be more efficient in the event of failure.

## GROBID over many .zip files

Want to use GNU/Parallel in a mode that will do retries well:

    fd .zip /srv/sandcrawler/tasks/crossref-pre-1909-scholarly-works/ | \
        sort | \
        parallel -j16 --progress --joblog extract_tasks.log --resume-failed \
        './grobid_tool.py --kafka-mode --kafka-env prod --kafka-hosts wbgrp-svc350.us.archive.org:9092,wbgrp-svc284.us.archive.org:9092,wbgrp-svc285.us.archive.org:9092 --grobid-host http://localhost:8070 extract-zipfile {}'

After starting, check that messages are actually getting pushed to kafka
(producer failures can be silent!). If anything goes wrong, run the exact same
command again. The sort is to ensure jobs are enqueued in the same order again;
could also dump `fd` output to a command file first.

