
status: wip

TODO:
x XML fulltext URL extractor (based on HTML biblio metadata, not PDF url extractor)
x differential JATS XML and scielo XML from generic XML?
    application/xml+jats is what fatcat is doing for abstracts
    but it should be application/jats+xml?
    application/tei+xml
    if startswith "<article " and "<article-meta>" => JATS
x refactor ingest worker to be more general
x have ingest code publish body to kafka topic
/ create/configure kafka topic
/ write a persist worker
- test everything locally
- fatcat: ingest tool to create requests
- fatcat: entity updates worker creates XML ingest requests for specific sources
- fatcat: ingest file import worker allows XML results
- ansible: deployment of persist worker

XML Fulltext Ingest
====================

This document details changes to include XML fulltext ingest in the same way
that we currently ingest PDF fulltext.

Currently this will just fetch the single XML document, which is often lacking
figures, tables, and other required files.

## Ingest Worker

Could either re-use HTML metadata extractor to fetch XML fulltext links, or
fork that code off to a separate method, like the PDF fulltext URL extractor.

Hopefully can re-use almost all of the PDF pipeline code, by making that ingest
worker class more generic and subclassing it.

Result objects are treated the same as PDF ingest results: the result object
has context about status, and if successful, file metadata and CDX row of the
terminal object.

TODO: should it be assumed that XML fulltext will end up in S3 bucket? or
should there be an `xml_meta` SQL table tracking this, like we have for PDFs
and HTML?

TODO: should we detect and specify the XML schema better? Eg, indicate if JATS.


## Persist Pipeline

### Kafka Topic

sandcrawler-ENV.xml-doc
    similar to other fulltext topics; JSON wrapping the XML
    key compaction, content compression

### S3/SeaweedFS

`sandcrawler` bucket, `xml` folder. Extension could depend on sub-type of XML?

### Persist Worker

New S3-only worker that pulls from kafka topic and pushes to S3. Works
basically the same as PDF persist in S3-only mode, or like pdf-text worker.
