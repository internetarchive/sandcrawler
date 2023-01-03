
status: deployed

XML Fulltext Ingest
====================

This document details changes to include XML fulltext ingest in the same way
that we currently ingest PDF fulltext.

Currently this will just fetch the single XML document, which is often lacking
figures, tables, and other required files.

## Text Encoding

Because we would like to treat XML as a string in a couple contexts, but XML
can have multiple encodings (indicated in an XML header), we are in a bit of a
bind. Simply parsing into unicode and then re-encoding as UTF-8 could result in
a header/content mismatch. Any form of re-encoding will change the hash of the
document. For recording in fatcat, the file metadata will be passed through.
For storing in Kafka and blob store (for downstream analysis), we will parse
the raw XML document (as "bytes") with an XML parser, then re-output with UTF-8
encoding. The hash of the *original* XML file will be used as the key for
referring to this document. This is unintuitive, but similar to what we are
doing with PDF and HTML documents (extracting in a useful format, but keeping
the original document's hash as a key).

Unclear if we need to do this re-encode process for XML documents already in
UTF-8 encoding.

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
