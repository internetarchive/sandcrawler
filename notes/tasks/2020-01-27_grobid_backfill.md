
Recently added a bunch of PDFs to sandcrawler-db. Want to GROBID extract the
~15m which haven't been processed yet. Also want to re-GROBID a batch of
PDFs-in-zipfiles from archive.org; will probably also want to re-GROBID other
petabox files soon.

## pre-1923 zipfile re-extraction

Exact commands (in parallel):

    fd .zip /srv/sandcrawler/tasks/crossref-pre-1909-scholarly-works/ | \
            parallel -j16 --progress --joblog extract_tasks.log --resume-failed \
            './grobid_tool.py --kafka-mode --kafka-env prod --kafka-hosts wbgrp-svc263.us.archive.org:9092,wbgrp-svc284.us.archive.org:9092,wbgrp-svc285.us.archive.org:9092 --grobid-host http://localhost:8070 extract-zipfile {}'

    fd .zip /srv/sandcrawler/tasks/crossref-pre-1923-scholarly-works/ | \
            parallel -j16 --progress --joblog extract_tasks_1923.log --resume-failed \
            './grobid_tool.py --kafka-mode --kafka-env prod --kafka-hosts wbgrp-svc263.us.archive.org:9092,wbgrp-svc284.us.archive.org:9092,wbgrp-svc285.us.archive.org:9092 --grobid-host http://localhost:8070 extract-zipfile {}'

## petabox re-extraction

This was run around 2020-02-03. There are a few million remaining PDFs that
have only partial file metadata (`file_meta`), meaning run with old version of
sandcrawler code. Want to get them all covered, maybe even DELETE the missing
ones, so re-grobiding petabox-only files.

There are about 2,887,834 files in petabox, only 46,232 need re-processing (!).

    psql sandcrawler < dump_regrobid_pdf_petabox.sql
    cat dump_regrobid_pdf_petabox.2020-02-03.json | sort -S 4G | uniq -w 40 | cut -f2 > dump_regrobid_pdf_petabox.2020-02-03.uniq.json

This is pretty few... maybe even would have been caught by wayback backfill?

Small start:

    head /srv/sandcrawler/tasks/dump_regrobid_pdf_petabox.2020-02-03.uniq.json | ./grobid_tool.py --kafka-env prod --kafka-hosts wbgrp-svc263.us.archive.org:9092,wbgrp-svc284.us.archive.org:9092,wbgrp-svc285.us.archive.org:9092 --kafka-mode --grobid-host http://localhost:8070 -j0 extract-json -

Full batch, 25x parallel:

    cat /srv/sandcrawler/tasks/dump_regrobid_pdf_petabox.2020-02-03.uniq.json | pv -l | parallel -j25 --pipe ./grobid_tool.py --kafka-env prod --kafka-hosts wbgrp-svc263.us.archive.org:9092,wbgrp-svc284.us.archive.org:9092,wbgrp-svc285.us.archive.org:9092 --kafka-mode --grobid-host http://localhost:8070 -j0 extract-json -

