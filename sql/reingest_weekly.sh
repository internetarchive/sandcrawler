#!/bin/bash

set -e              # fail on error
set -u              # fail if variable not set in substitution
set -o pipefail     # fail if part of a '|' command fails

sudo -u postgres psql sandcrawler < dump_reingest_weekly.sql

cd ../python
sudo -u sandcrawler pipenv run \
    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/reingest_weekly_current.rows.json \
    > /srv/sandcrawler/tasks/reingest_weekly_current.json

cat /srv/sandcrawler/tasks/reingest_weekly_current.json \
    | shuf \
    | head -n60000 \
    | jq . -c \
    | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-daily -p -1

