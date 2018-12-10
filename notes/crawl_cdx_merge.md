
## New Way

Run script from scratch repo:

    ~/scratch/bin/cdx_collection.py CRAWL-2000

    zcat CRAWL-2000.cdx.gz | wc -l

    # update crawl README/ANALYSIS/whatever

Assuming we're just looking at PDFs:

    zcat CRAWL-2000.cdx.gz | rg -i pdf | sort -u | gzip > CRAWL-2000.sorted.cdx.gz

## Old Way

Use metamgr to export an items list.

Get all the CDX files and merge/sort:

    mkdir CRAWL-2000 && cd CRAWL-2000
    cat ../CRAWL-2000.items | shuf | parallel --bar -j6 ia download {} {}.cdx.gz
    ls */*.cdx.gz | parallel --bar -j1 zcat {} > CRAWL-2000.unsorted.cdx
    sort -u CRAWL-2000.unsorted.cdx > CRAWL-2000.cdx
    wc -l CRAWL-2000.cdx
    rm CRAWL-2000.unsorted.cdx

    # gzip and upload to petabox, or send to HDFS, or whatever
