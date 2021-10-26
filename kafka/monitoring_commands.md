
    kafkacat -C -b wbgrp-svc284.us.archive.org:9092 -t sandcrawler-prod.ingest-file-results -o end | jq '[.status, .base_url]' -c

    kafkacat -C -b wbgrp-svc284.us.archive.org:9092 -t sandcrawler-prod.ingest-file-results -o end | jq '[.request.ingest_request_source, .status, .request.base_url, .terminal.terminal_url]' -c
