#!/bin/bash

set -e              # fail on error
set -u              # fail if variable not set in substitution
set -o pipefail     # fail if part of a '|' command fails

sudo -u postgres psql sandcrawler < dump_reingest_weekly.sql

cd ../python
pipenv run ./scripts/ingestrequest_row2json.py /grande/snapshots/reingest_weekly_spn2-error_current.rows.json | shuf > /grande/snapshots/reingest_weekly_spn2-error_current.json
pipenv run ./scripts/ingestrequest_row2json.py /grande/snapshots/reingest_weekly_cdx-error_current.rows.json | shuf > /grande/snapshots/reingest_weekly_cdx-error_current.json
#pipenv run ./scripts/ingestrequest_row2json.py /grande/snapshots/reingest_weekly_cdx-error_bulk_current.rows.json | shuf > /grande/snapshots/reingest_weekly_cdx-error_bulk_current.json
pipenv run ./scripts/ingestrequest_row2json.py /grande/snapshots/reingest_weekly_wayback-error_current.rows.json | shuf > /grande/snapshots/reingest_weekly_wayback-error_current.json
pipenv run ./scripts/ingestrequest_row2json.py /grande/snapshots/reingest_weekly_gateway-timeout.rows.json | shuf > /grande/snapshots/reingest_weekly_gateway-timeout.json
pipenv run ./scripts/ingestrequest_row2json.py /grande/snapshots/reingest_weekly_petabox-error_current.rows.json | shuf > /grande/snapshots/reingest_weekly_petabox-error_current.json

cat /grande/snapshots/reingest_weekly_spn2-error_current.json /grande/snapshots/reingest_weekly_cdx-error_current.json /grande/snapshots/reingest_weekly_wayback-error_current.json /grande/snapshots/reingest_weekly_petabox-error_current.json /grande/snapshots/reingest_weekly_gateway-timeout.json | shuf | head -n60000 | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests -p -1

#cat /grande/snapshots/reingest_weekly_cdx-error_bulk.json | shuf | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1

