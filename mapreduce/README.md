
Hadoop streaming map/reduce jobs written in python using the mrjob library.

## Development and Testing

System dependencies in addition to `../README.md`:

- `libjpeg-dev` (for wayback libraries)

Run the tests with:

    pipenv run pytest

Check test coverage with:

    pytest --cov --cov-report html
    # open ./htmlcov/index.html in a browser

TODO: GROBID and HBase during development?

## Extraction Task

TODO:

## Backfill Task

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
