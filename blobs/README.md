
This document describes sandcrawler/fatcat use of "blob store" infrastructure
for storing hundreds of millions of small files. For example, GROBID XML
documents, jpeg thumbnails of PDFs.

The basic feature requirements for this system are:

- don't need preservation data resiliency: all this data is derived from
  primary content, and is usually redundantly stored in Kafka topics (and thus
  can be re-indexed to any server bounded only by throughput of the object
  store service; Kafka is usually faster)
- don't require SSDs or large amounts of RAM. Ability to accelerate performance
  with additional RAM or moving indexes to SSD is nice, but we will be using
  spinning disks for primary data storage
- hundreds of millions or billions of objects, fetchable by a key we define
- optional transparent compression (for text and XML)
- typical object (file) size of 5-200 KBytes uncompressed, want to support up
  to several MBytes
- very simple internal API for GET/PUT (S3 API compatible is good)
- ability to proxy to HTTP publicly for reads (eg, HTTP fall-back with no
  authenticaiton), controllable by at least bucket granularity

## Infrastructure

`minio` was used initially, but did not scale well in number of files. We
currently use seaweedfs. Any S3-compatible key/value store should work in
theory. openlibrary.org has used WARCs in petabox items in the past. Actual
cloud object stores tend to be expensive for this kind of use case.

The facebook "haystack" project (and whitepaper) are good background reading
describing one type of system that works well for this application.


## Bucket / Folder Structure

Currently we run everything off a single server, with no redundancy. There is
no QA/prod distinction.

Setting access control and doing bulk deletions is easiest at the bucket level,
less easy at the folder level, most difficult at the suffix (file extention)
level.

For files that are derived from PDFs, we use the SHA-1 (in lower-case hex) of
the source PDF to contruct keys. We generate nested "directories" from the hash
to limit the number of keys per "directory" (even though in S3/seaweedfs there
are no actual directories involved). The structure looks like:

    <bucket>/<folder>/<byte0>/<byte1>/<sha1hex><suffix>

Eg:

    sandcrawler/grobid/1a/64/1a6462a925a9767b797fe6085093b6aa9f27f523.tei.xml

The nesting is sort of a hold-over from minio (where files were actually
on-disk), but seems worth keeping in case we end up switching storage systems
in the future.

## Existing Content

sandcrawler: internal/controlled access to PDF derivatives
    grobid: TEI-XML documents
        extension: .tei.xml
    text: raw pdftotext (or other text transform)
        extension: .txt

thumbnail: public bucket for thumbnail images
    pdf: thumbnails from PDF files
        extension: .180px.jpg

## Proxy and URLs

Internal HTTP access via:

    http://wbgrp-svc169.us.archive.org:8333/<bucket>/<key>

Public access via:

    https://blobs.fatcat.wiki/<bucket>/<key>

Eg:

    http://wbgrp-svc169.us.archive.org:8333/testing/small.txt
    http://wbgrp-svc169.us.archive.org:8333/sandcrawler/grobid/1a/64/1a6462a925a9767b797fe6085093b6aa9f27f523.tei.xml
    https://blobs.fatcat.wiki/testing/small.txt
    https://blobs.fatcat.wiki/thumbnail/pdf/1a/64/1a6462a925a9767b797fe6085093b6aa9f27f523.180px.jpg

