
Run tests:

    pipenv run python -m pytest

An example actually connecting to HBase from a local machine, with thrift
running on a devbox:

    ./backfill_hbase_from_cdx.py tests/files/example.cdx \
        --hbase-table wbgrp-journal-extract-0-qa \
        --hbase-host bnewbold-dev.us.archive.org

Actual invocation to run on Hadoop cluster (running on an IA devbox, where
hadoop environment is configured):

    # Create tarball of virtualenv
    pipenv shell
    tar -czf backfill-4OmRI0zZ.tar.gz -C /home/bnewbold/.local/share/virtualenvs/backfill-4OmRI0zZ .

    ./backfill_hbase_from_cdx.py \
        -r hadoop \
        --hbase-host bnewbold-dev.us.archive.org \
        --hbase-table wbgrp-journal-extract-0-qa \
        -c mrjob.conf \
        --archive backfill-4OmRI0zZ.tar.gz#venv \
        hdfs:///user/bnewbold/journal_crawl_cdx/citeseerx_crawl_2017.cdx
