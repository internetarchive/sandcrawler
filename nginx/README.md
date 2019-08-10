
This folder contains nginx configs for partner access to sandcrawler DB
(postgrest) and GROBID XML blobs (minio).

## Let's Encrypt

As... bnewbold?

    sudo certbot certonly \
        --non-interactive \
        --agree-tos \
        --email bnewbold@archive.org \
        --webroot -w /var/www/letsencrypt \
            -d sandcrawler-minio.fatcat.wiki \
            -d sandcrawler-db.fatcat.wiki

