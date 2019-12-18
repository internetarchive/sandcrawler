#!/usr/bin/env python3
"""
DEPRECATED: this worker uses old kafka topics and an old schema. Use
`sandcrawler_worker.py` instead.

Kafka worker that does GROBID extraction from one queue and into another.

Based on the ungrobided Hadoop job code. Does not talk to HBase at all, just
petabox and GROBID. Will delegate tasks to random GROBID workers.

Lines (tasks) are enqueued using a trivial kafkacat invocation; output is
persisted in Kakfa (in compressed format), and also drained into HBase by a
second worker.

Schema of tasks is the 'ungrobided' TSV output. Schema of output is JSON with
keys:

    "key": SHA1 in base32 with prefix, eg, "sha1:DLCCSMMVTCCIR6LRXHEQLZ4PWO6NG2YT"
    "grobid0:status_code": HTTP status code (integer)
    "grobid0:status": dict/json
    "grobid0:tei_xml": xml as a single string
    "f:c": dict/json from input
    "file:mime": string from input
    "file:cdx": dict/json from input
    # NOT grobid0:tei_json, grobid0:metadata, or grobid0:quality, which can be
    # re-derived from tei_xml

Requires:
- requests
- pykafka
- wayback/GWB libraries
"""

# XXX: some broken MRO thing going on in here due to python3 object wrangling
# in `wayback` library. Means we can't run pylint.
# pylint: skip-file

import os
import sys
import xml
import json
import raven
import struct
import argparse
import requests
import pykafka
import wayback.exception
from http.client import IncompleteRead
from wayback.resourcestore import ResourceStore
from gwb.loader import CDXLoaderFactory

from common import parse_ungrobided_line
from grobid2json import teixml2json

# Yep, a global. Gets DSN from `SENTRY_DSN` environment variable
sentry_client = raven.Client()

# Specific poison-pill rows we should skip
KEY_DENYLIST = (
    'sha1:DLCCSMMVTCCIR6LRXHEQLZ4PWO6NG2YT',    # "failed to guess ARC header format"
)

class KafkaGrobidWorker:

    def __init__(self, kafka_hosts, consume_topic, produce_topic, **kwargs):
        self.consume_topic = consume_topic
        self.produce_topic = produce_topic
        self.consumer_group = kwargs.get('consumer_group', 'grobid-extraction')
        self.kafka_hosts = kafka_hosts or 'localhost:9092'
        self.grobid_uri = kwargs.get('grobid_uri')
        # /serve/ instead of /download/ doesn't record view count
        self.petabox_base_url = kwargs.get('petabox_base_url', 'http://archive.org/serve/')
        # gwb library will fall back to reading from /opt/.petabox/webdata.secret
        self.petabox_webdata_secret = kwargs.get('petabox_webdata_secret', os.environ.get('PETABOX_WEBDATA_SECRET'))
        self.warc_uri_prefix = kwargs.get('warc_uri_prefix')
        self.mime_filter = ['application/pdf']
        self.rstore = None
        self.produce_max_request_size = 20000000  # Kafka producer batch size tuning; also limit on size of single extracted document

    def grobid_process_fulltext(self, content):
        r = requests.post(self.grobid_uri + "/api/processFulltextDocument",
            files={'input': content})
        return r

    def parse_line(self, raw_line):
        """Line should be TSV and have non-null fields:

            - key (string) (separated in Kafka case)
            - f:c (string, json)
            - file:mime (string)
            - file:cdx (string, json)
        """

        if (raw_line.startswith(' ') or raw_line.startswith('#') or raw_line.startswith('\t')):
            return None, dict(status="invalid", reason="line prefix", input=raw_line)

        info = parse_ungrobided_line(raw_line)
        if info is None:
            return None, dict(status="invalid", reason="ungrobided parse")

        if info['file:mime'] not in self.mime_filter:
            return None, dict(status="skip", reason="mimetype", mimetype=info['file:mime'])

        # If warc is not item/file.(w)arc.gz form, skip it
        if len(info['file:cdx']['warc'].split('/')) != 2:
            return None, dict(status="skip", reason="WARC path not petabox item/file", path=info['file:cdx']['warc'])

        return info, None

    def fetch_warc_content(self, warc_path, offset, c_size):
        warc_uri = self.warc_uri_prefix + warc_path
        if not self.rstore:
            self.rstore = ResourceStore(loaderfactory=CDXLoaderFactory(
                webdata_secret=self.petabox_webdata_secret,
                download_base_url=self.petabox_base_url))
        try:
            gwb_record = self.rstore.load_resource(warc_uri, offset, c_size)
        except wayback.exception.ResourceUnavailable:
            return None, dict(status="error",
                reason="failed to load file contents from wayback/petabox (ResourceUnavailable)")
        except ValueError as ve:
            return None, dict(status="error",
                reason="failed to load file contents from wayback/petabox (ValueError: {})".format(ve))
        except EOFError as eofe:
            return None, dict(status="error",
                reason="failed to load file contents from wayback/petabox (EOFError: {})".format(eofe))
        except TypeError as te:
            return None, dict(status="error",
                reason="failed to load file contents from wayback/petabox (TypeError: {}; likely a bug in wayback python code)".format(te))
        # Note: could consider a generic "except Exception" here, as we get so
        # many petabox errors. Do want jobs to fail loud and clear when the
        # whole cluster is down though.

        if gwb_record.get_status()[0] != 200:
            return None, dict(status="error",
                reason="archived HTTP response (WARC) was not 200",
                warc_status=gwb_record.get_status()[0])

        try:
            raw_content = gwb_record.open_raw_content().read()
        except IncompleteRead as ire:
            return None, dict(status="error",
                reason="failed to read actual file contents from wayback/petabox (IncompleteRead: {})".format(ire))
        return raw_content, None

    def extract(self, info):

        # Fetch data from WARCs in petabox
        original_content, status = self.fetch_warc_content(
            info['file:cdx']['warc'],
            info['file:cdx']['offset'],
            info['file:cdx']['c_size'])
        if status:
            return None, status

        info['file:size'] = len(original_content)

        # Submit to GROBID
        try:
            grobid_response = self.grobid_process_fulltext(original_content)
        except requests.exceptions.ConnectionError:
            return None, dict(status="error", reason="connection to GROBID worker")

        info['grobid0:status_code'] = grobid_response.status_code

        # 4 MByte XML size limit; don't record GROBID status on this path
        if len(grobid_response.content) > 4000000:
            info['grobid0:status'] = {'status': 'oversize'}
            return info, dict(status="oversize", reason="TEI response was too large")

        if grobid_response.status_code != 200:
            # response.text is .content decoded as utf-8
            info['grobid0:status'] = dict(status='error', description=grobid_response.text)
            return info, dict(status="error", reason="non-200 GROBID HTTP status",
                extra=grobid_response.text)

        info['grobid0:status'] = {'status': 'partial'}
        info['grobid0:tei_xml'] = grobid_response.content
        info['grobid0:status'] = {'status': 'success'}

        return info, None

    def do_work(self, raw_line):
        """
        1. parse filtered line
        2. fetch data from wayback
        3. submit to GROBID
          4. convert GROBID response to JSON (and metadata)
          6. determine "quality"
        6. produce result to kafka

        Returns: (grobid_output, status) (both are None or dict)
        If grobid_output is None, error was recovered, status returned.
        Otherwise, we were successful; grobid_output should be JSON serialized
        and published to kafka.
        """

        #self.increment_counter('lines', 'total')

        # Parse line and filter down
        info, status = self.parse_line(raw_line)
        if info is None:
            #self.increment_counter('lines', status['status'])
            return None, status
        key = info['key']
        if key in KEY_DENYLIST:
            #self.increment_counter('lines', 'denylist')
            return None, dict(status='denylist', key=key)

        # Note: this may not get "cleared" correctly
        sentry_client.extra_context(dict(
            row_key=key,
            cdx_url=info['file:cdx']['url'],
            cdx_dt=info['file:cdx']['dt'],
            cdx_warc=info['file:cdx']['warc'],
        ))

        # Do the extraction
        info, status = self.extract(info)
        if info is None:
            #self.increment_counter('lines', status['status'])
            status['key'] = key
            return None, status
        extraction_status = status

        # Need to encode 'bytes' as 'str' for JSON serialization
        if info.get('grobid0:tei_xml'):
            info['grobid0:tei_xml'] = info['grobid0:tei_xml'].decode('utf-8')

        #self.increment_counter('lines', 'success')

        grobid_status_code = info.get('grobid0:status_code', None)
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

        print("Starting Kafka GROBID extraction worker...")
        kafka = pykafka.KafkaClient(hosts=self.kafka_hosts, broker_version="2.0.0")
        produce_topic = kafka.topics[self.produce_topic]
        consume_topic = kafka.topics[self.consume_topic]

        sequential_failures = 0
        # Configure producer to basically *immediately* publish messages,
        # one-at-a-time, but asynchronously (don't block). Fetch and GROBID
        # process takes a while, and we want to send as soon as processing is
        # done.
        with produce_topic.get_producer(sync=False,
                                        compression=pykafka.common.CompressionType.GZIP,
                                        retry_backoff_ms=250,
                                        max_queued_messages=50,
                                        min_queued_messages=10,
                                        linger_ms=5000,
                                        max_request_size=self.produce_max_request_size) as producer:
            print("Producing to: {}".format(self.produce_topic))
            consumer = consume_topic.get_balanced_consumer(
                consumer_group=self.consumer_group,
                managed=True,
                auto_commit_enable=True,
                auto_commit_interval_ms=30000, # 30 seconds
                # LATEST because best to miss processing than waste time re-process
                auto_offset_reset=pykafka.common.OffsetType.LATEST,
                queued_max_messages=50,
                compacted_topic=True)
            print("Consuming from: {} as {}".format(self.consume_topic, self.consumer_group))
            sys.stdout.flush()
            for msg in consumer:
                grobid_output, status = self.do_work(msg.value.decode('utf-8'))
                if grobid_output:
                    print("extracted {}: {}".format(
                        grobid_output.get('key'),
                        status))
                    sys.stdout.flush()
                    producer.produce(json.dumps(grobid_output, sort_keys=True).encode('utf-8'))
                    sequential_failures = 0
                else:
                    sys.stderr.write("failed to extract: {}\n".format(status))
                    sequential_failures += 1
                    if sequential_failures > 20:
                        sys.stderr.write("too many failures in a row, bailing out\n")
                        sys.exit(-1)


@sentry_client.capture_exceptions
def main():

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--kafka-hosts',
                        default="localhost:9092",
                        help="list of Kafka brokers (host/port) to use")
    parser.add_argument('--kafka-env',
                        default="qa",
                        help="eg, 'qa' or 'prod'")
    parser.add_argument('--consume-topic',
                        default=None,
                        help="Kafka topic to consume from")
    parser.add_argument('--produce-topic',
                        default=None,
                        help="Kafka topic to produce to")
    parser.add_argument('--grobid-uri',
                        type=str,
                        default='http://localhost:8070',
                        help='URI of GROBID API Server')
    parser.add_argument('--warc-uri-prefix',
                        type=str,
                        default='https://archive.org/serve/',
                        help='URI where WARCs can be found')
    args = parser.parse_args()

    if args.consume_topic is None:
        args.consume_topic = "sandcrawler-{}.ungrobided".format(args.kafka_env)
    if args.produce_topic is None:
        args.produce_topic = "sandcrawler-{}.grobid-output".format(args.kafka_env)

    worker = KafkaGrobidWorker(**args.__dict__)
    worker.run()

if __name__ == '__main__': # pragma: no cover
    main()
