#!/bin/bash

set -e              # fail on error
set -u              # fail if variable not set in substitution
# can't use pipefail here because under normal operations kafkacat will exit
# code with a 141 (indicating that a pipe ran out of stuff for it to read).
# this will always trigger this file to report failure and thus lead to
# perpetually failing this when used in a systemd service.
#set -o pipefail     # fail if part of a '|' command fails

sudo -u postgres psql sandcrawler < dump_reingest_quarterly.sql

cd ../python
sudo -u sandcrawler pipenv run \
    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/reingest_quarterly_current.rows.json \
    > /srv/sandcrawler/tasks/reingest_quarterly_current.json

cat /srv/sandcrawler/tasks/reingest_quarterly_current.json \
    | shuf \
    | head -n120000 \
    | jq . -c \
    | kafkacat -P -b wbgrp-svc350.us.archive.org -t sandcrawler-prod.ingest-file-requests-daily -p -1

