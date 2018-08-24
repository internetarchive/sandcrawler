
Hadoop streaming map/reduce jobs written in python using the mrjob library.

## Development and Testing

System dependencies on Linux (ubuntu/debian):

    sudo apt install -y python3-dev python3-pip python3-wheel libjpeg-dev build-essential
    pip3 install --user pipenv

On macOS (using Homebrew):

    brew install libjpeg pipenv

You probably need `~/.local/bin` on your `$PATH`.

Fetch all python dependencies with:

    pipenv install --dev

Run the tests with:

    pipenv run pytest

Check test coverage with:

    pytest --cov --cov-report html
    # open ./htmlcov/index.html in a browser

## Running Python Jobs on Hadoop

The `../please` script automates these steps; you should use that instead.

When running python streaming jobs on the actual hadoop cluster, we need to
bundle along our python dependencies in a virtual env tarball. Building this
tarball can be done like:

    export PIPENV_VENV_IN_PROJECT=1
    pipenv install --deploy
    tar -czf venv-current.tar.gz -C .venv ."""

### Extraction Task

An example actually connecting to HBase from a local machine, with thrift
running on a devbox and GROBID running on a dedicated machine:

    ./extraction_cdx_grobid.py \
        --hbase-table wbgrp-journal-extract-0-qa \
        --hbase-host wbgrp-svc263.us.archive.org \
        --grobid-uri http://wbgrp-svc096.us.archive.org:8070 \
        tests/files/example.cdx

Running from the cluster (once a ./venv-current.tar.gz tarball exists):

    ./extraction_cdx_grobid.py \
        --hbase-table wbgrp-journal-extract-0-qa \
        --hbase-host wbgrp-svc263.us.archive.org \
        --grobid-uri http://wbgrp-svc096.us.archive.org:8070 \
        -r hadoop \
        -c mrjob.conf \
        --archive venv-current.tar.gz#venv \
        hdfs:///user/bnewbold/journal_crawl_cdx/citeseerx_crawl_2017.cdx

### Backfill Task

An example actually connecting to HBase from a local machine, with thrift
running on a devbox:

    ./backfill_hbase_from_cdx.py \
        --hbase-table wbgrp-journal-extract-0-qa \
        --hbase-host wbgrp-svc263.us.archive.org \
        tests/files/example.cdx

Running from the cluster (once a ./venv-current.tar.gz tarball exists):

    ./backfill_hbase_from_cdx.py \
        --hbase-host wbgrp-svc263.us.archive.org \
        --hbase-table wbgrp-journal-extract-0-qa \
        -r hadoop \
        -c mrjob.conf \
        --archive venv-current.tar.gz#venv \
        hdfs:///user/bnewbold/journal_crawl_cdx/citeseerx_crawl_2017.cdx
