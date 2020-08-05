
Want to clean up missing/partial processing (GROBID, `pdf_meta`, `file_meta`)
in sandcrawler database.


## `pdf_meta` for petabox rows

Ran `dump_unextracted_pdf_petabox.sql` SQL, which resulted in a .json file.

    wc -l dump_unextracted_pdf_petabox.2020-07-22.json
    1503086 dump_unextracted_pdf_petabox.2020-07-22.json

Great, 1.5 million, not too many. Start small:

    head -n1000 dump_unextracted_pdf_petabox.2020-07-22.json | rg -v "\\\\" | jq . -c | pv -l | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.unextracted -p -1

Full batch:

    cat dump_unextracted_pdf_petabox.2020-07-22.json | rg -v "\\\\" | jq . -c | pv -l | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.unextracted -p -1

## `pdf_meta` missing CDX rows

First, the GROBID-ized rows but only if has a fatcat file as well.

10,755,365! That is a lot still to process.

    cat dump_unextracted_pdf.fatcat.2020-07-22.json | rg -v "\\\\" | jq . -c | pv -l | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.unextracted -p -1

## `GROBID` missing petabox rows

    wc -l /grande/snapshots/dump_ungrobided_pdf_petabox.2020-07-22.json 
    972221 /grande/snapshots/dump_ungrobided_pdf_petabox.2020-07-22.json

Start small:

    head -n1000 dump_ungrobided_pdf_petabox.2020-07-22.json | rg -v "\\\\" | jq . -c | pv -l | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ungrobided-pg -p -1

Full batch:

    cat dump_ungrobided_pdf_petabox.2020-07-22.json | rg -v "\\\\" | jq . -c | pv -l | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ungrobided-pg -p -1

## `GROBID` for missing CDX rows in fatcat

    wc -l dump_ungrobided_pdf.fatcat.2020-07-22.json
    1808580 dump_ungrobided_pdf.fatcat.2020-07-22.json

Full batch:

    cat dump_ungrobided_pdf.fatcat.2020-07-22.json | rg -v "\\\\" | jq . -c | pv -l | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ungrobided-pg -p -1

## `GROBID` for bad status

Eg, wayback errors.

TODO

## `pdf_trio` for OA journal crawls

TODO

## `pdf_trio` for "included by heuristic", not in fatcat

TODO

## Live-ingest missing arxiv papers

    ./fatcat_ingest.py --allow-non-oa --limit 10000 query arxiv_id:* > /srv/fatcat/snapshots/arxiv_10k_ingest_requests.json
    => Expecting 1505184 release objects in search queries

    cat /srv/fatcat/snapshots/arxiv_10k_ingest_requests.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests -p 22

Repeating this every few days should (?) result in all the backlog of arxiv
papers getting indexed. Could focus on recent years to start (with query
filter).

## re-ingest spn2 errors (all time)

Eg:

    spn2-cdx-lookup-failure: 143963
    spn-error: 101773
    spn2-error: 16342

TODO

## re-try CDX errors

Eg, for unpaywall only, bulk ingest all `cdx-error`.

TODO

## live ingest unpaywall `no-capture` URLs

After re-trying the CDX errors for unpaywall URLs (see above), count all the
no-capture URLs, and if reasonable recrawl them all in live more ("reasonable"
meaning fewer than 200k or so URLs).

Could also force recrawl (not using CDX lookups) for some publisher platforms
if that made sense.

TODO
