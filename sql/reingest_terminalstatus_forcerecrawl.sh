#!/bin/bash

set -e              # fail on error
set -u              # fail if variable not set in substitution
set -o pipefail     # fail if part of a '|' command fails

sudo -u postgres psql sandcrawler < dump_reingest_terminalstatus.sql

cd ../python
sudo -u sandcrawler pipenv run \
    ./scripts/ingestrequest_row2json.py --force-recrawl /srv/sandcrawler/tasks/reingest_terminalstatus_current.rows.json \
    > /srv/sandcrawler/tasks/reingest_terminalstatus_current.json

cat /srv/sandcrawler/tasks/reingest_terminalstatus_current.json \
    | shuf \
    | head -n100000 \
    | jq . -c \
    | kafkacat -P -b wbgrp-svc350.us.archive.org -t sandcrawler-prod.ingest-file-requests-daily -p -1

