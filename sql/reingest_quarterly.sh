#!/bin/bash

set -e              # fail on error
set -u              # fail if variable not set in substitution
set -o pipefail     # fail if part of a '|' command fails

sudo -u postgres psql sandcrawler < dump_reingest_quarterly.sql

cd ../python
sudo -u sandcrawler pipenv run ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/reingest_quarterly_spn2-error_current.rows.json | shuf > /srv/sandcrawler/tasks/reingest_quarterly_spn2-error_current.json
sudo -u sandcrawler pipenv run ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/reingest_quarterly_cdx-error_current.rows.json | shuf > /srv/sandcrawler/tasks/reingest_quarterly_cdx-error_current.json
#sudo -u sandcrawler pipenv run ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/reingest_quarterly_cdx-error_bulk_current.rows.json | shuf > /srv/sandcrawler/tasks/reingest_quarterly_cdx-error_bulk_current.json
sudo -u sandcrawler pipenv run ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/reingest_quarterly_wayback-error_current.rows.json | shuf > /srv/sandcrawler/tasks/reingest_quarterly_wayback-error_current.json
sudo -u sandcrawler pipenv run ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/reingest_quarterly_gateway-timeout.rows.json | shuf > /srv/sandcrawler/tasks/reingest_quarterly_gateway-timeout.json
sudo -u sandcrawler pipenv run ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/reingest_quarterly_petabox-error_current.rows.json | shuf > /srv/sandcrawler/tasks/reingest_quarterly_petabox-error_current.json

cat /srv/sandcrawler/tasks/reingest_quarterly_spn2-error_current.json /srv/sandcrawler/tasks/reingest_quarterly_cdx-error_current.json /srv/sandcrawler/tasks/reingest_quarterly_wayback-error_current.json /srv/sandcrawler/tasks/reingest_quarterly_petabox-error_current.json /srv/sandcrawler/tasks/reingest_quarterly_gateway-timeout.json | shuf | head -n250000 | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-daily -p -1

#cat /srv/sandcrawler/tasks/reingest_quarterly_cdx-error_bulk.json | shuf | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

