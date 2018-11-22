#!/usr/bin/env python3
"""
Kafka worker that consumes GROBID output from Kafka and pushes into HBase.

Based on the ungrobided Hadoop job code.

TODO: binary conversion in 'grobided' topic? shouldn't be, do that here, as well as all TEI extraction/parsing

Requires:
- requests
- pykafka
"""

# XXX: some broken MRO thing going on in here due to python3 object wrangling
# in `wayback` library. Means we can't run pylint.
# pylint: skip-file

import sys
import xml
import json
import raven
import struct
import requests
import argparse
import happybase
import pykafka

from common import parse_ungrobided_line
from grobid2json import teixml2json

# Yep, a global. Gets DSN from `SENTRY_DSN` environment variable
sentry_client = raven.Client()

# Specific poison-pill rows we should skip
KEY_DENYLIST = (
    'sha1:DLCCSMMVTCCIR6LRXHEQLZ4PWO6NG2YT',    # "failed to guess ARC header format"
)

class KafkaGrobidHbaseWorker:

    def __init__(self, kafka_hosts, consume_topic, **kwargs):
        self.consume_topic = consume_topic
        self.consumer_group = kwargs.get('consumer_group', 'grobid-hbase-insert')
        self.kafka_hosts = kafka_hosts or 'localhost:9092'

    def do_work(self, raw_line):
        """
        1. parse info JSON (with XML inside)
        2. do XML -> JSON conversions
        3. push to HBase

        Returns: ???
        """

        # Parse line and filter down
        info = json.loads(raw_line)
        key = info['key']
        if key in KEY_DENYLIST:
            #self.increment_counter('lines', 'denylist')
            return None, dict(status='denylist', key=key)

        # Note: this may not get "cleared" correctly
        sentry_client.extra_context(dict(row_key=key))

        # Need to decode 'str' back in to 'bytes' (from JSON serialization)
        if info.get('grobid0:tei_xml'):
            info['grobid0:tei_xml'] = info['grobid0:tei_xml'].encode('utf-8')

        # Convert TEI XML to JSON
        try:
            info['grobid0:tei_json'] = teixml2json(info['grobid0:tei_xml'], encumbered=True)
        except xml.etree.ElementTree.ParseError:
            info['grobid0:status'] = dict(status="fail", reason="GROBID 200 XML parse error")
            return info, info['grobid0:status']
        except ValueError:
            info['grobid0:status'] = dict(status="fail", reason="GROBID 200 XML non-TEI content")
            return info, info['grobid0:status']

        tei_metadata = info['grobid0:tei_json'].copy()
        for k in ('body', 'annex'):
            # Remove fulltext (copywritted) content
            tei_metadata.pop(k, None)
        info['grobid0:metadata'] = tei_metadata

        # Decide what to bother inserting back into HBase
        # Basically, don't overwrite backfill fields.
        grobid_status_code = info.get('grobid0:status_code', None)
        for k in list(info.keys()):
            if k.encode('utf-8') in ('f:c', 'file:mime', 'file:cdx'):
                info.pop(k)

        # Convert fields to binary
        for k in list(info.keys()):
            if info[k] is None:
                info.pop(k)
            # NOTE: we're not actually sending these f:*, file:* keys...
            elif k in ('f:c', 'file:cdx', 'grobid0:status', 'grobid0:tei_json',
                    'grobid0:metadata'):
                assert type(info[k]) == dict
                info[k] = json.dumps(info[k], sort_keys=True, indent=None)
            elif k in ('file:size', 'grobid0:status_code'):
                # encode as int64 in network byte order
                if info[k] != {} and info[k] != None:
                    info[k] = struct.pack('!q', info[k])

        key = info.pop('key')
        self.hb_table.put(key, info)
        #self.increment_counter('lines', 'success')

        if extraction_status is not None:
            return info, dict(status="partial", key=key,
                grobid_status_code=grobid_status_code,
                reason=extraction_status['reason'])
        else:
            return info, dict(status="success",
                grobid_status_code=grobid_status_code, key=key,
                extra=extraction_status)

    def run(self):

        # 1. start consumer (in managed/balanced fashion, with consumer group)
        # 2. for each thingie, do the work; if success publish to kafka; either
        #    way... print? log?
        # 3. repeat!

        kafka = pykafka.KafkaClient(hosts=self.kafka_hosts, broker_version="1.0.0")
        consume_topic = kafka.topics[self.consume_topic]

        print("starting up...")
        sequential_failures = 0
        consumer = consume_topic.get_balanced_consumer(
            consumer_group=self.consumer_group,
            managed=True,
            auto_commit_enable=True,
            compacted_topic=True)
        for msg in consumer:
            print("got a line! ")
            grobid_output, status = self.do_work(msg.value.decode('utf-8'))
            if grobid_output:
                sequential_failures = 0
            else:
                print("failed to extract: {}".format(status))
                sequential_failures += 1
                if sequential_failures > 20:
                    print("too many failures in a row, bailing out")
                    sys.exit(-1)


@sentry_client.capture_exceptions
def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--kafka-hosts',
                        default="localhost:9092",
                        help="list of Kafka brokers (host/port) to use")
    parser.add_argument('--kafka-env',
                        default="qa",
                        help="eg, 'qa' or 'prod'")
    parser.add_argument('--consume-topic',
                        default=None,
                        help="Kafka topic to consume from")
    parser.add_argument('--hbase-table',
                        type=str,
                        default='wbgrp-journal-extract-0-qa',
                        help='HBase table to backfill into (must exist)')
    parser.add_argument('--hbase-host',
                        type=str,
                        default='localhost',
                        help='HBase thrift API host to connect to')
    args = parser.parse_args()

    if args.consume_topic is None:
        args.consume_topic = "sandcrawler-{}.ungrobided".format(args.kafka_env)

    worker = KafkaGrobidHbaseWorker(**args.__dict__)
    worker.run()

if __name__ == '__main__': # pragma: no cover
    main()
