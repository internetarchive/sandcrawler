
Want to do priority crawling of Ukranian web content, plus Russia and Belarus.


## What is Missing?

    (country_code:ua OR lang:uk)
    => 2022-03-08, before ingests: 470,986 total, 170,987 missing, almost all article-journal, peak in 2019, 55k explicitly OA
    => later in day, already some 22k missing found! wow


## Metadata Prep

- container metadata update (no code changes)
    x  wikidata SPARQL update
    x  chocula run
    x  journal metadata update (fatcat)
    x  update journal stats (fatcat extra)
- DOAJ article metadata import
    x  prep and upload single JSON file


## Journal Homepage URL Crawl

x dump ukraine-related journal homepages from chocula DB
x create crawl config
x start crawl
x repeat for belarus and russia


    python3 -m chocula export_urls > homepage_urls.2022-03-08.tsv
    cat homepage_urls.2022-03-08.tsv | cut -f2 | rg '\.ua/' | sort -u > homepage_urls.2022-03-08.ua_tld.tsv
    wc -l homepage_urls.2022-03-08.ua_tld.tsv
    1550 homepage_urls.2022-03-08.ua_tld.tsv

    cat homepage_urls.2022-03-08.tsv | cut -f2 | rg '\.by/' | sort -u > homepage_urls.2022-03-08.by_tld.tsv
    cat homepage_urls.2022-03-08.tsv | cut -f2 | rg '\.ru/' | sort -u > homepage_urls.2022-03-08.ru_tld.tsv

sqlite3:

    select count(*) from journal where country = 'ua' or lang = 'uk' or name like '%ukrain%' or publi
    1952

    SELECT COUNT(*) FROM homepage
    LEFT JOIN journal ON homepage.issnl = journal.issnl
    WHERE
        journal.country = 'ua'
        OR journal.lang = 'uk'
        OR journal.name like '%ukrain%'
        OR journal.publisher like '%ukrain%';
    => 1970

    .mode csv
    .once homepage_urls_ukraine.tsv
    SELECT homepage.url FROM homepage
    LEFT JOIN journal ON homepage.issnl = journal.issnl
    WHERE
        journal.country = 'ua'
        OR journal.lang = 'uk'
        OR journal.name like '%ukrain%'
        OR journal.publisher like '%ukrain%';

    .mode csv
    .once homepage_urls_russia.tsv
    SELECT homepage.url FROM homepage
    LEFT JOIN journal ON homepage.issnl = journal.issnl
    WHERE
        journal.country = 'ru'
        OR journal.lang = 'ru'
        OR journal.name like '%russ%'
        OR journal.publisher like '%russ%';

    .mode csv
    .once homepage_urls_belarus.tsv
    SELECT homepage.url FROM homepage
    LEFT JOIN journal ON homepage.issnl = journal.issnl
    WHERE
        journal.country = 'by'
        OR journal.lang = 'be'
        OR journal.name like '%belarus%'
        OR journal.publisher like '%belarus%';

    cat homepage_urls_ukraine.tsv homepage_urls.2022-03-08.ua_tld.tsv | sort -u > homepage_urls_ukraine_combined.2022-03-08.tsv

    wc -l homepage_urls.2022-03-08.ua_tld.tsv homepage_urls_ukraine.tsv homepage_urls_ukraine_combined.2022-03-08.tsv 
        1550 homepage_urls.2022-03-08.ua_tld.tsv
        1971 homepage_urls_ukraine.tsv
        3482 homepage_urls_ukraine_combined.2022-03-08.tsv

    cat homepage_urls_russia.tsv homepage_urls.2022-03-08.ru_tld.tsv | sort -u > homepage_urls_russia_combined.2022-03-08.tsv

    wc -l homepage_urls_russia.tsv homepage_urls.2022-03-08.ru_tld.tsv homepage_urls_russia_combined.2022-03-08.tsv
        3728 homepage_urls_russia.tsv
        2420 homepage_urls.2022-03-08.ru_tld.tsv
        6030 homepage_urls_russia_combined.2022-03-08.tsv


    cat homepage_urls_belarus.tsv homepage_urls.2022-03-08.by_tld.tsv | sort -u > homepage_urls_belarus_combined.2022-03-08.tsv

    wc -l homepage_urls_belarus.tsv homepage_urls.2022-03-08.by_tld.tsv homepage_urls_belarus_combined.2022-03-08.tsv
        138 homepage_urls_belarus.tsv
        85 homepage_urls.2022-03-08.by_tld.tsv
        222 homepage_urls_belarus_combined.2022-03-08.tsv


## Landing Page Crawl

x create crawl config
x fatcat ingest query for related URLs
    => special request code/label?
x finish .by and .ru article URL dump, start crawling
x URL list filtered from new OAI-PMH feed
    => do we need to do full bulk load/dump, or not?
- URL list from partner (google)
- do we need to do alternative thing of iterating over containers, ingesting each?

    ./fatcat_ingest.py --env prod \
        --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --kafka-request-topic sandcrawler-prod.ingest-file-requests-bulk \
        --ingest-type pdf \
        --allow-non-oa \
        query "country_code:ua OR lang:uk"

    # around Tue 08 Mar 2022 01:07:37 PM PST
    # Expecting 185659 release objects in search queries
    # didn't complete successfully? hrm

    # ok, retry "manually" (with kafkacat)
    ./fatcat_ingest.py --env prod \
        --ingest-type pdf \
        --allow-non-oa \
        query "country_code:ua OR lang:uk" \
    | pv -l \
    | gzip \
    > /srv/fatcat/ingest_ua_pdfs.2022-03-08.requests.json
    # Counter({'elasticsearch_release': 172881, 'estimate': 172881, 'ingest_request': 103318})
    # 103k 0:25:04 [68.7 /s]

    zcat /srv/fatcat/ingest_ua_pdfs.2022-03-08.requests.json \
        | rg -v "\\\\" \
        | jq . -c \
        | pv -l \
        | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

    zcat ingest_ua_pdfs.2022-03-08.requests.json.gz | jq .base_url -r | sort -u | pv -l | gzip > ingest_ua_pdfs.2022-03-08.txt.gz
    # 103k 0:00:02 [38.1k/s]

    ./fatcat_ingest.py --env prod \
        --ingest-type pdf \
        --allow-non-oa \
        query "country_code:by OR lang:be" \
    | pv -l \
    | gzip \
    > /srv/fatcat/tasks/ingest_by_pdfs.2022-03-09.requests.json.gz
    # Expecting 2266 release objects in search queries
    # 1.29k 0:00:34 [37.5 /s]

    zcat /srv/fatcat/tasks/ingest_by_pdfs.2022-03-09.requests.json.gz \
        | rg -v "\\\\" \
        | jq . -c \
        | pv -l \
        | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

    zcat ingest_by_pdfs.2022-03-09.requests.json.gz | jq .base_url -r | sort -u | pv -l | gzip > ingest_by_pdfs.2022-03-09.txt.gz

    ./fatcat_ingest.py --env prod \
        --ingest-type pdf \
        --allow-non-oa \
        query "country_code:ru OR lang:ru" \
    | pv -l \
    | gzip \
    > /srv/fatcat/tasks/ingest_ru_pdfs.2022-03-09.requests.json.gz
    # Expecting 1515246 release objects in search queries

    zcat /srv/fatcat/tasks/ingest_ru_pdfs.2022-03-09.requests.partial.json.gz \
        | rg -v "\\\\" \
        | jq . -c \
        | pv -l \
        | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

    zcat ingest_ru_pdfs.2022-03-09.requests.partial.json.gz | jq .base_url -r | sort -u | pv -l | gzip > ingest_ru_pdfs.2022-03-09.txt.gz


    zstdcat oai_pmh_partial_dump_2022_03_01_urls.txt.zst | rg '\.ua/' | pv -l > oai_pmh_partial_dump_2022_03_01_urls.ua_tld.txt
    # 309k 0:00:03 [81.0k/s]

    zstdcat oai_pmh_partial_dump_2022_03_01_urls.txt.zst | rg '\.by/' | pv -l > oai_pmh_partial_dump_2022_03_01_urls.by_tld.txt
    # 71.2k 0:00:03 [19.0k/s]

    zstdcat oai_pmh_partial_dump_2022_03_01_urls.txt.zst | rg '\.ru/' | pv -l > oai_pmh_partial_dump_2022_03_01_urls.ru_tld.txt
    # 276k 0:00:03 [72.9k/s]

## Outreach

- openalex
- sucho.org
- ceeol.com
