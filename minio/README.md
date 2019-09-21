
minio is used as an S3-compatible blob store. Initial use case is GROBID XML
documents, addressed by the sha1 of the PDF file the XML was extracted from.

Note that on the backend minio is just storing objects as files on disk.

## Buckets

Notable buckets, and structure/naming convention:

    grobid/
        2c/0d/2c0daa9307887a27054d4d1f137514b0fa6c6b2d.tei.xml
        SHA1 (lower-case hex) of PDF that XML was extracted from
    unpaywall/grobid/
        2c/0d/2c0daa9307887a27054d4d1f137514b0fa6c6b2d.tei.xml
        SHA1 (lower-case hex) of PDF that XML was extracted from
        (mirror of /grobid/ for which we crawled for unpaywall and made publicly accessible)

Create new buckets like:

    mc mb sandcrawler/grobid

## Users

Create a new readonly user like:

    mc admin user add sandcrawler unpaywall $RANDOM_SECRET_KEY readonly

Make a prefix within a bucket world-readable like:

    mc policy set download sandcrawler/unpaywall/grobid
