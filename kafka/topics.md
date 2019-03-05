
This file lists all the Kafka topics currently used by sandcrawler (and
fatcat).

NOTE: should use `.` or `_` in topic names, but not both. We chose to use `.`

ENV below is one of `prod` or `qa`.


## Topic List

All topics should default to `snappy` compression on-disk, and indefinite
retention (on both a size and time basis).

    sandcrawler-ENV.ungrobided
        => PDF files in IA needing GROBID processing
        => 50x partitions (huge! for worker parallelism)
        => key: "sha1:<base32>"

    sandcrawler-ENV.grobid-output
        => output of GROBID processing (from pdf-ungrobided feed)
        => could get big; 16x partitions (to distribute data)
        => use GZIP compression (worth the overhead)
        => key: "sha1:<base32>"; could compact

    fatcat-ENV.api-crossref
    fatcat-ENV.api-datacite
        => all new and updated DOIs (regardless of type)
        => full raw crossref/datacite API objects (JSON)
        => key: lower-case DOI
        => ~1TB capacity; 8x crossref partitions, 4x datacite
        => key compaction possible

    fatcat-ENV.oaipmh-pubmed
    fatcat-ENV.oaipmh-arxiv
    fatcat-ENV.oaipmh-doaj-journals (DISABLED)
    fatcat-ENV.oaipmh-doaj-articles (DISABLED)
        => OAI-PMH harvester output
        => full XML resource output (just the <<record> part?)
        => key: identifier
        => ~1TB capacity; 4x-8x partitions
        => key compaction possible

    fatcat-ENV.api-crossref-state
    fatcat-ENV.api-datacite-state
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

    fatcat-ENV.release-updates
        => contains "fully" expanded JSON objects
        => key: fcid
        => 8x partitions


## Create fatcat QA topics

If you run these commands for an existing topic, you'll get something like
`Error while executing topic command : Topic 'fatcat-qa.changelog' already
exists`; this seems safe, and the settings won't be over-ridden.

    ssh misc-vm
    cd /srv/kafka-broker/kafka_2.12-2.0.0/bin/

    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 50 --topic sandcrawler-qa.ungrobided
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 16 --topic sandcrawler-qa.grobid-output --config compression.type=gzip

    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 1 --topic fatcat-qa.changelog
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 8 --topic fatcat-qa.release-updates
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 8 --topic fatcat-qa.work-updates
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 4 --topic fatcat-qa.file-updates
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 4 --topic fatcat-qa.container-updates

    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 8 --topic fatcat-qa.api-crossref
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 8 --topic fatcat-qa.api-datacite
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 1 --topic fatcat-qa.api-crossref-state
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 1 --topic fatcat-qa.api-datacite-state

    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 4 --topic fatcat-qa.oaipmh-pubmed
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 4 --topic fatcat-qa.oaipmh-arxiv
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 1 --topic fatcat-qa.oaipmh-pubmed-state
    ./kafka-topics.sh --create --zookeeper localhost:2181 --replication-factor 2 --partitions 1 --topic fatcat-qa.oaipmh-arxiv-state

