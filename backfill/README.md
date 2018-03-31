
Run tests:

    pipenv run python -m pytest

An example actually connecting to HBase from a local machine, with thrift
running on a devbox:

    ./backfill_hbase_from_cdx.py tests/files/example.cdx \
        --hbase-table wbgrp-journal-extract-0-qa \
        --hbase-host bnewbold-dev.us.archive.org

