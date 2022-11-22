
Had a huge number of SPN requests for the andrzejklimczuk.com domain,
presumably from the author.

Many were duplicates (same file, multiple releases, often things like zenodo
duplication). Many were also GROBID 500s, due to truncated common crawl
captures.

Needed to cleanup! Basically sorted through a few editgroups manually, then
rejected all the rest and manually re-submitted with the below queries and
commands:

    SELECT COUNT(*) from ingest_request
    LEFT JOIN ingest_file_result ON
        ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    LEFT JOIN grobid ON
        grobid.sha1hex = ingest_file_result.terminal_sha1hex
    WHERE
        ingest_request.link_source = 'spn'
        AND ingest_request.ingest_type = 'pdf'
        AND ingest_request.base_url like 'https://andrzejklimczuk.com/%';
    => 589

    SELECT ingest_file_result.status, COUNT(*) from ingest_request
    LEFT JOIN ingest_file_result ON
        ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    LEFT JOIN grobid ON
        grobid.sha1hex = ingest_file_result.terminal_sha1hex
    WHERE
        ingest_request.link_source = 'spn'
        AND ingest_request.ingest_type = 'pdf'
        AND ingest_request.base_url like 'https://andrzejklimczuk.com/%'
    GROUP BY ingest_file_result.status;

         status     | count 
    ----------------+-------
     cdx-error      |     1
     success        |   587
     wrong-mimetype |     1
    (3 rows)


    SELECT grobid.status_code, COUNT(*) from ingest_request
    LEFT JOIN ingest_file_result ON
        ingest_file_result.ingest_type = ingest_request.ingest_type
        AND ingest_file_result.base_url = ingest_request.base_url
    LEFT JOIN grobid ON
        grobid.sha1hex = ingest_file_result.terminal_sha1hex
    WHERE
        ingest_request.link_source = 'spn'
        AND ingest_request.ingest_type = 'pdf'
        AND ingest_request.base_url like 'https://andrzejklimczuk.com/%'
    GROUP BY grobid.status_code;

     status_code | count 
    -------------+-------
             200 |   385
             500 |   202
                 |     2
    (3 rows)


    COPY (
        SELECT row_to_json(ingest_request.*) FROM ingest_request
        LEFT JOIN ingest_file_result ON
            ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        LEFT JOIN grobid ON
            grobid.sha1hex = ingest_file_result.terminal_sha1hex
        WHERE
            ingest_request.link_source = 'spn'
            AND ingest_request.ingest_type = 'pdf'
            AND ingest_request.base_url like 'https://andrzejklimczuk.com/%'
            AND ingest_file_result.status = 'success'
            AND grobid.status_code = 500
    ) TO '/srv/sandcrawler/tasks/andrzejklimczuk_bad_spn.rows.json';
    => COPY 202

    COPY (
        SELECT row_to_json(ingest_request.*) FROM ingest_request
        LEFT JOIN ingest_file_result ON
            ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        LEFT JOIN grobid ON
            grobid.sha1hex = ingest_file_result.terminal_sha1hex
        WHERE
            ingest_request.link_source = 'spn'
            AND ingest_request.ingest_type = 'pdf'
            AND ingest_request.base_url like 'https://andrzejklimczuk.com/%'
            AND ingest_file_result.status = 'success'
            AND grobid.status_code = 200
    ) TO '/srv/sandcrawler/tasks/andrzejklimczuk_good_spn.rows.json';
    => COPY 385

sudo -u sandcrawler pipenv run \
    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/andrzejklimczuk_good_spn.rows.json \
    > /srv/sandcrawler/tasks/andrzejklimczuk_good_spn.json

sudo -u sandcrawler pipenv run \
    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/andrzejklimczuk_bad_spn.rows.json \
    | jq '. + {force_recrawl: true}' -c \
    > /srv/sandcrawler/tasks/andrzejklimczuk_bad_spn.json

cat /srv/sandcrawler/tasks/andrzejklimczuk_bad_spn.json \
    | shuf \
    | head -n60000 \
    | jq . -c \
    | kafkacat -P -b wbgrp-svc350.us.archive.org -t sandcrawler-prod.ingest-file-requests-priority -p -1

cat /srv/sandcrawler/tasks/andrzejklimczuk_good_spn.json \
    | shuf \
    | head -n100 \
    | jq . -c \
    | kafkacat -P -b wbgrp-svc350.us.archive.org -t sandcrawler-prod.ingest-file-requests-priority -p -1

cat /srv/sandcrawler/tasks/andrzejklimczuk_good_spn.json \
    | shuf \
    | head -n10000 \
    | jq . -c \
    | kafkacat -P -b wbgrp-svc350.us.archive.org -t sandcrawler-prod.ingest-file-requests-priority -p -1

sudo -u sandcrawler pipenv run \
    ./scripts/ingestrequest_row2json.py /srv/sandcrawler/tasks/andrzejklimczuk_bad_spn.rows.json \
    > /srv/sandcrawler/tasks/andrzejklimczuk_bad2_spn.json

cat /srv/sandcrawler/tasks/andrzejklimczuk_bad2_spn.json \
    | shuf \
    | head -n60000 \
    | jq . -c \
    | kafkacat -P -b wbgrp-svc350.us.archive.org -t sandcrawler-prod.ingest-file-requests-priority -p -1
