
Generate ingest requests from arabesque:

    zcat /data/arabesque/ARXIV-CRAWL-2019-10.arabesque.json.gz | ./arabesque2ingestrequest.py --link-source arxiv --extid-type arxiv --release-stage submitted - | shuf > /data/arabesque/ARXIV-CRAWL-2019-10.arabesque.ingest_request.json

    zcat /data/arabesque/PUBMEDCENTRAL-CRAWL-2019-10.arabesque.json.gz | ./arabesque2ingestrequest.py --link-source pmc --extid-type pmcid - | shuf > /data/arabesque/PUBMEDCENTRAL-CRAWL-2019-10.arabesque.ingest_request.json


Quick tests locally:

    time head -n100 /data/arabesque/ARXIV-CRAWL-2019-10.arabesque.ingest_request.json |./ingest_file.py requests - > sample_arxiv.json
    time head -n100 /data/arabesque/PUBMEDCENTRAL-CRAWL-2019-10.arabesque.ingest_request.json |./ingest_file.py requests - > sample_pubmed.json

These are all wayback success; looking good! Single threaded, from home laptop
(over tunnel), took about 9 minutes, or 5.5sec/pdf. That's pretty slow even
with 30x parallelism. Should re-test on actual server. GROBID pre-check should
help?

With new bulk topic:

    head PUBMEDCENTRAL-CRAWL-2019-10.arabesque.ingest_request.json -n1000 | kafkacat -P -b localhost -t sandcrawler-prod.ingest-file-requests-bulk -p -1

Ok, let them rip:

    cat PUBMEDCENTRAL-CRAWL-2019-10.arabesque.ingest_request.json -n1000 | kafkacat -P -b localhost -t sandcrawler-prod.ingest-file-requests-bulk -p -1
    cat ARXIV-CRAWL-2019-10.arabesque.ingest_request.json | kafkacat -P -b localhost -t sandcrawler-prod.ingest-file-requests-bulk -p -1
