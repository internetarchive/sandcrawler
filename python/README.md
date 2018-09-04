
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

## Troubleshooting

If you get pipenv errors like:

    AttributeError: '_NamespacePath' object has no attribute 'sort'
        
    ----------------------------------------

    Command "python setup.py egg_info" failed with error code 1 in /1/tmp/pip-install-h7lb6tqz/proto-google-cloud-datastore-v1/

     ☤  ▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉ 0/8 — 00:00:03
     bnewbold@bnewbold-dev$ 
     bnewbold@bnewbold-dev$ pipenv install --deploy --dev
     Installing dependencies from Pipfile.lock (e82980)…
     An error occurred while installing proto-google-cloud-logging-v2==0.91.3! Will try again.
     An error occurred while installing gapic-google-cloud-error-reporting-v1beta1==0.15.3! Will try again.
     An error occurred while installing gapic-google-cloud-datastore-v1==0.15.3! Will try again.
     An error occurred while installing proto-google-cloud-datastore-v1==0.90.4! Will try again.

Then something has gone horribly wrong with your pip/pipenv/python setup. Don't
have a good workaround yet.

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
