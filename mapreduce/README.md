
Hadoop streaming map/reduce jobs written in python using the mrjob library.

## Development and Testing

System dependencies in addition to `../README.md`:

- `libjpeg-dev` (for wayback libraries)

Run the tests with:

    pipenv run pytest

Check test coverage with:

    pytest --cov --cov-report html
    # open ./htmlcov/index.html in a browser

TODO: Persistant GROBID and HBase during development? Or just use live
resources?

## Extraction Task

An example actually connecting to HBase from a local machine, with thrift
running on a devbox and GROBID running on a dedicated machine:

    ./extraction_cdx_grobid.py \
        --hbase-table wbgrp-journal-extract-0-qa \
        --hbase-host bnewbold-dev.us.archive.org \
        --grobid-uri http://wbgrp-svc096.us.archive.org:8070 \
        tests/files/example.cdx

Running from the cluster:

    # Create tarball of virtualenv
    pipenv shell
    export VENVSHORT=`basename $VIRTUAL_ENV`
    tar -czf $VENVSHORT.tar.gz -C /home/bnewbold/.local/share/virtualenvs/$VENVSHORT .

    ./extraction_cdx_grobid.py \
        --hbase-table wbgrp-journal-extract-0-qa \
        --hbase-host bnewbold-dev.us.archive.org \
        --grobid-uri http://wbgrp-svc096.us.archive.org:8070 \
        -r hadoop \
        -c mrjob.conf \
        --archive $VENVSHORT.tar.gz#venv \
        hdfs:///user/bnewbold/journal_crawl_cdx/citeseerx_crawl_2017.cdx

## Backfill Task

An example actually connecting to HBase from a local machine, with thrift
running on a devbox:

    ./backfill_hbase_from_cdx.py \
        --hbase-table wbgrp-journal-extract-0-qa \
        --hbase-host bnewbold-dev.us.archive.org \
        tests/files/example.cdx

Actual invocation to run on Hadoop cluster (running on an IA devbox, where
hadoop environment is configured):

    # Create tarball of virtualenv
    pipenv shell
    export VENVSHORT=`basename $VIRTUAL_ENV`
    tar -czf $VENVSHORT.tar.gz -C /home/bnewbold/.local/share/virtualenvs/$VENVSHORT .

    ./backfill_hbase_from_cdx.py \
        --hbase-host bnewbold-dev.us.archive.org \
        --hbase-table wbgrp-journal-extract-0-qa \
        -r hadoop \
        -c mrjob.conf \
        --archive $VENVSHORT.tar.gz#venv \
        hdfs:///user/bnewbold/journal_crawl_cdx/citeseerx_crawl_2017.cdx
