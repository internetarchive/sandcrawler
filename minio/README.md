
minio is used as an S3-compatible blob store. Initial use case is GROBID XML
documents, addressed by the sha1 of the PDF file the XML was extracted from.

Note that on the backend minio is just storing objects as files on disk.

## Buckets and Directories

Hosts and buckets:

    localhost:sandcrawler-dev
        create locally for development (see below)

    cluster:sandcrawler
        main sandcrawler storage bucket, for GROBID output and other derivatives.
        Note it isn't "sandcrawler-prod", for backwards compatibility reasons.

    cluster:sandcrawler-qa
        for, eg, testing on cluster servers

    cluster:unpaywall
        subset of sandcrawler content crawled due to unpaywall URLs;
        potentially made publicly accessible

Directory structure within sandcrawler buckets:

    grobid/2c/0d/2c0daa9307887a27054d4d1f137514b0fa6c6b2d.tei.xml
        SHA1 (lower-case hex) of PDF that XML was extracted from

Create new buckets like:

    mc mb cluster/sandcrawler-qa

## Development

Run minio server locally, with non-persisted data:

    docker run -p 9000:9000 minio/minio server /data

Credentials are `minioadmin:minioadmin`. Install `mc` client utility, and
configure:

    mc config host add localhost http://localhost:9000 minioadmin minioadmin

Then create dev bucket:

    mc mb --ignore-existing localhost/sandcrawler-dev

A common "gotcha" with `mc` command is that it will first look for a local
folder/directory with same name as the configured remote host, so make sure
there isn't a `./localhost` folder.


## Users

Create a new readonly user like:

    mc admin user add sandcrawler unpaywall $RANDOM_SECRET_KEY readonly

Make a prefix within a bucket world-readable like:

    mc policy set download cluster/unpaywall/grobid

