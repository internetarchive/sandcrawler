
This file lists all the Kafka topics currently used by sandcrawler (and
fatcat).

NOTE: should use `.` or `_` in topic names, but not both. We chose to use `.`

ENV below is one of `prod` or `qa`.


## Topic List

All topics should default to `snappy` compression on-disk, and indefinite
retention (on both a size and time basis).

    sandcrawler-ENV.grobid-output-pg
        => output of GROBID processing using grobid_tool.py
        => schema is sandcrawler-db style JSON: TEI-XML as a field
        => expected to be large; 12 partitions
        => use GZIP compression (worth the overhead)
        => key is sha1hex of PDF; enable key compaction

    sandcrawler-ENV.ungrobided-pg
        => PDF files in IA needing GROBID processing
        => schema is sandcrawler-db style JSON. Can be either `cdx` or `petabox` object
        => fewer partitions with batch mode, but still a bunch (24?)
        => key is sha1hex of PDF. enable time compaction (6 months?)

    sandcrawler-ENV.ingest-file-requests-daily
        => was ingest-file-requests previously, but renamed/rebalanced
        => ingest requests from multiple sources; mostly continuous or pseudo-interactive
        => schema is JSON; see ingest proposal for fields. small objects.
        => fewer partitions with batch mode, but still a bunch (24)
        => can't think of a good key, so none. enable time compaction (3-6 months?)

    sandcrawler-ENV.ingest-file-requests-bulk
        => ingest requests from bulk crawl sources; background processing
        => same as ingest-file-requests

    sandcrawler-ENV.ingest-file-requests-priority
        => ingest requests from bulk crawl sources; background processing
        => same as ingest-file-requests

    sandcrawler-ENV.ingest-file-results
        => ingest requests from multiple sources
        => schema is JSON; see ingest proposal for fields. small objects.
        => 6 partitions
        => can't think of a good key, so none; no compaction

    sandcrawler-ENV.pdftrio-output
        => output of each pdftrio ML classification
        => schema is JSON; see pdftrio proposal for fields. small objects.
        => 6 partitions
        => key is sha1hex of PDF; enable key compaction

    sandcrawler-ENV.unextracted
        => PDF files in IA needing extraction (thumbnails and text)
        => schema is sandcrawler-db style JSON. Can be either `cdx` or `petabox` object
        => fewer partitions with batch mode, but still a bunch (12? 24?)
        => key is sha1hex of PDF. enable time compaction (6 months?)

    sandcrawler-ENV.pdf-text
        => fulltext (raw text) and PDF metadata for pdfs
        => schema is JSON; see pdf_meta proposal for fields. large objects.
        => 12 partitions
        => key is sha1hex of PDF; enable key compaction; gzip compression

    sandcrawler-ENV.xml-doc
        => fulltext XML; mostly JATS XML
        => schema is JSON, with 'jats_xml' field containing the XML as a string
        => 6 partitions
        => key is sha1hex of XML document; enable key compaction; gzip compression

    sandcrawler-ENV.html-teixml
        => extracted fulltext from HTML; mostly TEI-XML
        => schema is JSON, with 'tei_xml' field containing the XML as a string
        => 6 partitions
        => key is sha1hex of source HTML document; enable key compaction; gzip compression

    sandcrawler-ENV.pdf-thumbnail-SIZE-TYPE
        => thumbnail images (eg, png, jpg) from PDFs
        => raw bytes in message (no JSON or other wrapping). fields average 10 KByte
        => 12 partitions; expect a TByte or so total
        => key is sha1hex of PDF; enable key compaction; no compression

    fatcat-ENV.api-crossref
    fatcat-ENV.api-datacite
        => all new and updated DOIs (regardless of type)
        => full raw crossref/datacite API objects (JSON)
        => key: lower-case DOI
        => ~1TB capacity; 8x crossref partitions, 4x datacite
        => key compaction possible

    fatcat-ENV.ftp-pubmed
        => new citations from FTP server, from: ftp://ftp.ncbi.nlm.nih.gov/pubmed/updatefiles/
        => raw XML, one record per message (PubmedArticle, up to 25k records/day and 650MB/day)
        => key: PMID
        => key compaction possible

    fatcat-ENV.api-crossref-state
    fatcat-ENV.api-datacite-state
    fatcat-ENV.ftp-pubmed-state
    fatcat-ENV.oaipmh-pubmed-state
    fatcat-ENV.oaipmh-arxiv-state
    fatcat-ENV.oaipmh-doaj-journals-state (DISABLED)
    fatcat-ENV.oaipmh-doaj-articles-state (DISABLED)
        => serialized harvester state for ingesters
        => custom JSON
        => key: timespan? nothing to start
        => 1x partitions; time/space limit Ok

    fatcat-ENV.changelog
        => small-ish objects (not fully expanded/hydrated)
        => single partition
        => key: could be changelog index (integer, as string)

    fatcat-ENV.release-updates-v03
        => contains "fully" expanded JSON objects
        => v03 is newer v0.3.0 API schema (backwards incompatible)
        => key: fcid
        => 8x partitions
    fatcat-ENV.container-updates
        => key: fcid
        => 4x partitions
    fatcat-ENV.file-updates
        => key: fcid
        => 4x partitions
    fatcat-ENV.work-ident-updates
        => work identifiers when updated and needs re-indexing (eg, in scholar)
        => 6x partitions
        => key: doc ident ("work_{ident}")
        => key compaction possible; long retention

    scholar-ENV.sim-updates
        => 6x partitions
        => key: "sim_item_{}"
        => key compaction possible; long retention
    scholar-ENV.update-docs
        => 12x partitions
        => key: scholar doc identifer
        => gzip compression
        => key compaction possible
        => short time-based retention (2 months?)

### Deprecated/Unused Topics

    sandcrawler-ENV.ungrobided
        => PDF files in IA needing GROBID processing
        => 50x partitions (huge! for worker parallelism)
        => key: "sha1:<base32>"

    sandcrawler-ENV.grobid-output
        => output of GROBID processing (from pdf-ungrobided feed)
        => could get big; 16x partitions (to distribute data)
        => use GZIP compression (worth the overhead)
        => key: "sha1:<base32>"; could compact

    fatcat-ENV.oaipmh-pubmed
    fatcat-ENV.oaipmh-arxiv
    fatcat-ENV.oaipmh-doaj-journals (DISABLED)
    fatcat-ENV.oaipmh-doaj-articles (DISABLED)
        => OAI-PMH harvester output
        => full XML resource output (just the <<record> part?)
        => key: identifier
        => ~1TB capacity; 4x-8x partitions
        => key compaction possible

## Create fatcat QA topics

If you run these commands for an existing topic, you'll get something like
`Error while executing topic command : Topic 'fatcat-qa.changelog' already
exists`; this seems safe, and the settings won't be over-ridden.

    ssh misc-vm
    cd /srv/kafka-broker/kafka_2.12-2.0.0/bin/

    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 24 --topic sandcrawler-qa.ungrobided-pg
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 12 --topic sandcrawler-qa.grobid-output-pg --config compression.type=gzip --config cleanup.policy=compact

    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 24 --topic sandcrawler-qa.ingest-file-requests-daily --config retention.ms=7889400000 --config cleanup.policy=delete
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 12 --topic sandcrawler-qa.ingest-file-requests-bulk --config retention.ms=7889400000 --config cleanup.policy=delete
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions  6 --topic sandcrawler-qa.ingest-file-requests-priority --config retention.ms=7889400000 --config cleanup.policy=delete
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions  6 --topic sandcrawler-qa.ingest-file-results

    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 6 --topic sandcrawler-qa.pdftrio-output --config cleanup.policy=compact

    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 1 --topic fatcat-qa.changelog
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 8 --topic fatcat-qa.release-updates-v03
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 4 --topic fatcat-qa.file-updates
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 4 --topic fatcat-qa.container-updates
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 6 --topic fatcat-qa.work-ident-updates

    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 8 --topic fatcat-qa.api-crossref
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 8 --topic fatcat-qa.api-datacite --config cleanup.policy=compact
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 8 --topic fatcat-qa.ftp-pubmed --config cleanup.policy=compact
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 1 --topic fatcat-qa.api-crossref-state
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 1 --topic fatcat-qa.api-datacite-state
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 1 --topic fatcat-qa.ftp-pubmed-state

    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 4 --topic fatcat-qa.oaipmh-pubmed
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 4 --topic fatcat-qa.oaipmh-arxiv
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 1 --topic fatcat-qa.oaipmh-pubmed-state
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 1 --topic fatcat-qa.oaipmh-arxiv-state

    # only 3 partitions in QA
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 12 --topic sandcrawler-qa.pdf-text --config compression.type=gzip --config cleanup.policy=compact
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 12 --topic sandcrawler-qa.pdf-thumbnail-180px-jpg --config cleanup.policy=compact
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 24 --topic sandcrawler-qa.unextracted

    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 6 --topic scholar-qa.sim-updates
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 12 --topic scholar-qa.update-docs --config compression.type=gzip --config cleanup.policy=compact --config retention.ms=7889400000

    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 6 --topic sandcrawler-qa.xml-doc --config compression.type=gzip --config cleanup.policy=compact
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 6 --topic sandcrawler-qa.html-teixml --config compression.type=gzip --config cleanup.policy=compact

