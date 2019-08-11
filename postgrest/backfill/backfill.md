
SQL Backfill Notes
-----------------------

GROBID is going to be somewhat complex.

TODO:
x CDX backfill script (CDX to postgresql direct, bulk inserts, python)
x `file_meta` bulk insert (TSV to postgresql direct, bulk upserts, python)
x GROBID insert (python, dump TSV to minio then postgresql)

## `cdx`

    #cat example.cdx | rg ' 200 ' | cut -d' ' -f2,3,4,6,9,10,11
    #cat example.cdx | rg ' 200 ' | awk '{print $6 "\t" $3 "\t" $2 "\t" $4 "\t\t" $6 "\t" $11 "\t" $9 "\t" $10}' | b32_hex.py | awk '{print $2 "\t" $3 "\t" $4 "\t" $1 "\t" $6 "\t" $7 "\t" $8}' > cdx.example.tsv
    cat example.cdx | ./filter_transform_cdx.py > cdx.example.tsv

    COPY cdx (url, datetime, sha1hex, mimetype, warc_path, warc_csize, warc_offset) FROM '/sandcrawler-db/backfill/cdx/cdx.example.tsv' WITH (FORMAT TEXT, DELIMITER E'\t', NULL '');

Big HDFS import:

    # but actually didn't import those; don't want to need to re-import
    hdfs dfs -get journal_crawl_cdx/*

    cat citeseerx_crawl_2017.cdx | rg ' 200 ' | ./filter_transform_cdx.py > cdx.citeseerx_crawl_2017.tsv
    cat gwb-pdf-20171227034923-surt-filter/* | rg ' 200 ' | ./filter_transform_cdx.py > gwb-pdf-20171227034923-surt-filter.tsv
    cat UNPAYWALL-PDF-CRAWL-2018-07.filtered.cdx | rg ' 200 ' | ./filter_transform_cdx.py > cdx.UNPAYWALL-PDF-CRAWL-2018-07.filtered.tsv
    cat MSAG-PDF-CRAWL-2017.cdx | rg ' 200 ' | ./filter_transform_cdx.py > cdx.MSAG-PDF-CRAWL-2017.tsv

    cat CORE-UPSTREAM-CRAWL-2018-11.sorted.cdx | rg ' 200 ' | ./filter_transform_cdx.py > cdx.CORE-UPSTREAM-CRAWL-2018-11.sorted.tsv
    cat DIRECT-OA-CRAWL-2019.pdfs.cdx | rg ' 200 ' | ./filter_transform_cdx.py > cdx.DIRECT-OA-CRAWL-2019.pdfs.tsv
    cat DOI-LANDING-CRAWL-2018-06.200_pdf.cdx | rg ' 200 ' | ./filter_transform_cdx.py > cdx.DOI-LANDING-CRAWL-2018-06.200_pdf.tsv
    cat OA-JOURNAL-TESTCRAWL-TWO-2018.pdf.cdx | rg ' 200 ' | ./filter_transform_cdx.py > cdx.OA-JOURNAL-TESTCRAWL-TWO-2018.pdf.tsv
    cat SEMSCHOLAR-PDF-CRAWL-2017.cdx | rg ' 200 ' | ./filter_transform_cdx.py > cdx.SEMSCHOLAR-PDF-CRAWL-2017.tsv
    cat TARGETED-PDF-CRAWL-2017.cdx | rg ' 200 ' | ./filter_transform_cdx.py > cdx.TARGETED-PDF-CRAWL-2017.tsv
    cat UNPAYWALL-PDF-CRAWL-2019-04.pdfs_sorted.cdx | rg ' 200 ' | ./filter_transform_cdx.py > cdx.UNPAYWALL-PDF-CRAWL-2019-04.pdfs_sorted.tsv

TODO: nasty escaping?

In psql:

    COPY cdx (url, datetime, sha1hex, mimetype, warc_path, warc_csize, warc_offset) FROM '/sandcrawler-db/backfill/cdx/cdx.UNPAYWALL-PDF-CRAWL-2018-07.filtered.tsv' WITH (FORMAT TEXT, DELIMITER E'\t', NULL '');
    # ERROR
    COPY cdx (url, datetime, sha1hex, mimetype, warc_path, warc_csize, warc_offset) FROM '/sandcrawler-db/backfill/cdx/cdx.MSAG-PDF-CRAWL-2017.tsv' WITH (FORMAT TEXT, DELIMITER E'\t', NULL '');
    # ERROR
    COPY cdx (url, datetime, sha1hex, mimetype, warc_path, warc_csize, warc_offset) FROM '/sandcrawler-db/backfill/cdx/cdx.citeseerx_crawl_2017.tsv' WITH (FORMAT TEXT, DELIMITER E'\t', NULL '');
    # COPY 1653840
    COPY cdx (url, datetime, sha1hex, mimetype, warc_path, warc_csize, warc_offset) FROM '/sandcrawler-db/backfill/cdx/cdx.CORE-UPSTREAM-CRAWL-2018-11.sorted.tsv' WITH (FORMAT TEXT, DELIMITER E'\t', NULL '');
    # COPY 2827563
    COPY cdx (url, datetime, sha1hex, mimetype, warc_path, warc_csize, warc_offset) FROM '/sandcrawler-db/backfill/cdx/cdx.DIRECT-OA-CRAWL-2019.pdfs.tsv' WITH (FORMAT TEXT, DELIMITER E'\t', NULL '');
    # COPY 10651736
    COPY cdx (url, datetime, sha1hex, mimetype, warc_path, warc_csize, warc_offset) FROM '/sandcrawler-db/backfill/cdx/cdx.DOI-LANDING-CRAWL-2018-06.200_pdf.tsv' WITH (FORMAT TEXT, DELIMITER E'\t', NULL '');
    # COPY 768565
    COPY cdx (url, datetime, sha1hex, mimetype, warc_path, warc_csize, warc_offset) FROM '/sandcrawler-db/backfill/cdx/cdx.OA-JOURNAL-TESTCRAWL-TWO-2018.pdf.tsv' WITH (FORMAT TEXT, DELIMITER E'\t', NULL '');
    # COPY 5310017
    COPY cdx (url, datetime, sha1hex, mimetype, warc_path, warc_csize, warc_offset) FROM '/sandcrawler-db/backfill/cdx/cdx.SEMSCHOLAR-PDF-CRAWL-2017.tsv' WITH (FORMAT TEXT, DELIMITER E'\t', NULL '');
    # COPY 2219839
    COPY cdx (url, datetime, sha1hex, mimetype, warc_path, warc_csize, warc_offset) FROM '/sandcrawler-db/backfill/cdx/cdx.TARGETED-PDF-CRAWL-2017.tsv' WITH (FORMAT TEXT, DELIMITER E'\t', NULL '');
    # ERROR
    COPY cdx (url, datetime, sha1hex, mimetype, warc_path, warc_csize, warc_offset) FROM '/sandcrawler-db/backfill/cdx/cdx.UNPAYWALL-PDF-CRAWL-2019-04.pdfs_sorted.tsv' WITH (FORMAT TEXT, DELIMITER E'\t', NULL '');
    # ERROR

NOTE: these largely didn't work; will need to write a batch importer.

Batch import process:

    cat UNPAYWALL-PDF-CRAWL-2018-07.filtered.cdx MSAG-PDF-CRAWL-2017.cdx TARGETED-PDF-CRAWL-2017.cdx UNPAYWALL-PDF-CRAWL-2019-04.pdfs_sorted.cdx | ./backfill_cdx.py
    # Done: Counter({'raw_lines': 123254127, 'total': 51365599, 'batches': 51365})

## `fatcat_file`

    zcat file_export.2019-07-07.json.gz | pv -l | jq -r 'select(.sha1 != null) | [.sha1, .ident, .release_ids[0]] | @tsv' | sort -S 8G | uniq -w 40 > /sandcrawler-db/backfill/fatcat_file.2019-07-07.tsv

In psql:

    COPY fatcat_file FROM '/sandcrawler-db/backfill/fatcat_file.2019-07-07.tsv' WITH (FORMAT TEXT, DELIMITER E'\t', NULL '');
    # => COPY 24727350

## `file_meta`

    zcat /fast/download/file_export.2019-07-07.json.gz | pv -l | jq -r 'select(.md5 != null) | [.sha1, .sha256, .md5, .size, .mimetype] | @tsv' | sort -S 8G | uniq -w 40 > /sandcrawler-db/backfill/file_meta.2019-07-07.tsv

In psql:

    COPY file_meta FROM '/sandcrawler-db/backfill/file_meta.2019-07-07.tsv' WITH (FORMAT TEXT, DELIMITER E'\t', NULL '');
    # -> COPY 5860092

## `petabox`

    zcat /fast/download/file_export.2019-07-07.json.gz | rg '//archive.org/' | pigz > /fast/download/file_export.2019-07-07.petabox.json.gz
    zcat /fast/download/file_export.2019-07-07.petabox.json.gz | ./petabox_transform.py | sort -u -S 8G | awk '{print $3 "\t" $1 "\t" $2}' | uniq -s40 | awk '{print $2 "\t" $3 "\t" $1}' > petabox.fatcat_2019-07-07.tsv

In psql:

    COPY petabox FROM '/sandcrawler-db/backfill/petabox.fatcat_2019-07-07.tsv' WITH (FORMAT TEXT, DELIMITER E'\t', NULL '');
    # -> COPY 2887834

## `grobid`

Quick test:

    zcat /bigger/unpaywall-transfer/2019-07-17-1741.30-dumpgrobidxml/part-00000.gz | cut -f2 | head | ./backfill_grobid.py

Run big batch:

    ls /bigger/unpaywall-transfer/2019-07-17-1741.30-dumpgrobidxml/part*gz | parallel --progress -j8 'zcat {} | cut -f2 | ./backfill_grobid.py'
    # [...]
    # Done: Counter({'minio-success': 161605, 'total': 161605, 'raw_lines': 161605, 'batches': 161})
    # [...]

Was running slow with lots of iowait and 99% jdb2. This seems to be disk I/O. Going to try:

    sudo mount /dev/sdc1 /sandcrawler-minio/ -o data=writeback,noatime,nobarrier

    # -j8: 20+ M/s write, little jdb2
    # -j16: 30+ M/s write, little jdb2
    # -j12: 30+ M/s write, going with this

For general use should go back to:

    sudo mount /dev/sdc1 /sandcrawler-minio/ -o data=noatime

    # -j4: Still pretty slow, only ~3-5 M/s disk write. jbd2 consistently at 99%, 360 K/s write

## rough table sizes

                              table_name                          | table_size | indexes_size | total_size 
    --------------------------------------------------------------+------------+--------------+------------
     "public"."cdx"                                               | 11 GB      | 8940 MB      | 20 GB
     "public"."shadow"                                            | 8303 MB    | 7205 MB      | 15 GB
     "public"."fatcat_file"                                       | 5206 MB    | 2094 MB      | 7300 MB
     "public"."file_meta"                                         | 814 MB     | 382 MB       | 1196 MB
     "public"."petabox"                                           | 403 MB     | 594 MB       | 997 MB
    [...]

