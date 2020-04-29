
import sys
import json
import time
import signal
import zipfile
import multiprocessing.pool
from collections import Counter
from confluent_kafka import Consumer, Producer, KafkaException

from .misc import parse_cdx_line
from .ia import SandcrawlerBackoffError


class SandcrawlerWorker(object):
    """
    Base class for sandcrawler workers.

    Usually these get "pushed" into by a RecordPusher. Output goes to another
    worker (pipeline-style), or defaults to stdout.
    """

    def __init__(self):
        self.counts = Counter()
        self.sink = None
        # TODO: self.counters

    def push_record(self, task):
        self.counts['total'] += 1
        result = self.process(task)
        if not result:
            self.counts['failed'] += 1
            return
        elif type(result) == dict and 'status' in result and len(result['status']) < 32:
            self.counts[result['status']] += 1

        if self.sink:
            self.sink.push_record(result)
            self.counts['pushed'] += 1
        else:
            print(json.dumps(result))
        return result

    def timeout_response(self, task):
        """
        This should be overridden by workers that want to return something
        meaningful when there is a processing timeout. Eg, JSON vs some other
        error message.
        """
        return None

    def push_record_timeout(self, task, timeout=300):
        """
        A wrapper around self.push_record which sets a timeout.

        Note that this uses signals and *will behave wrong/weirdly* with
        multithreading or if signal-based timeouts are used elsewhere in the
        same process.
        """

        def timeout_handler(signum, frame):
            raise TimeoutError("timeout processing record")
        signal.signal(signal.SIGALRM, timeout_handler)
        resp = None
        signal.alarm(int(timeout))
        try:
            resp = self.push_record(task)
        except TimeoutError:
            self.counts['timeout'] += 1
            resp = self.timeout_response(task) # pylint: disable=assignment-from-none
            # TODO: what if it is this push_record() itself that is timing out?
            if resp and self.sink:
                self.sink.push_record(resp)
                self.counts['pushed'] += 1
            elif resp:
                print(json.dumps(resp))
        finally:
            signal.alarm(0)
        return resp

    def push_batch(self, tasks):
        results = []
        for task in tasks:
            results.append(self.push_record(task))
        return results

    def finish(self):
        if self.sink:
            self.sink.finish()
        print("Worker: {}".format(self.counts), file=sys.stderr)
        return self.counts

    def process(self, task):
        """
        Derived workers need to implement business logic here.
        """
        raise NotImplementedError('implementation required')

class MultiprocessWrapper(SandcrawlerWorker):

    def __init__(self, worker, sink, jobs=None):
        self.counts = Counter()
        self.worker = worker
        self.sink = sink
        self.pool = multiprocessing.pool.Pool(jobs)

    def push_batch(self, tasks):
        self.counts['total'] += len(tasks)
        print("... processing batch of: {}".format(len(tasks)), file=sys.stderr)
        results = self.pool.map(self.worker.process, tasks)
        for result in results:
            if not result:
                self.counts['failed'] += 1
                return
            elif type(result) == dict and 'status' in result and len(result['status']) < 32:
                self.counts[result['status']] += 1

            if self.sink:
                self.sink.push_record(result)
                self.counts['pushed'] += 1
            else:
                print(json.dumps(result))
        return results

    def finish(self):
        self.pool.terminate()
        if self.sink:
            self.sink.finish()
        worker_counts = self.worker.finish()
        print("Multiprocessing: {}".format(self.counts), file=sys.stderr)
        return worker_counts

class BlackholeSink(SandcrawlerWorker):
    """
    Dummy SandcrawlerWorker. That doesn't do or process anything.

    Useful for tests.
    """

    def push_record(self, task):
        return

    def push_batch(self, tasks):
        return

class KafkaSink(SandcrawlerWorker):

    def __init__(self, kafka_hosts, produce_topic, **kwargs):
        self.sink = None
        self.counts = Counter()
        self.produce_topic = produce_topic
        self.kafka_hosts = kafka_hosts

        config = self.producer_config({
            'bootstrap.servers': kafka_hosts,
            'message.max.bytes': 30000000, # ~30 MBytes; broker is ~50 MBytes
            'api.version.request': True,
            'api.version.fallback.ms': 0,
        })
        self.producer = Producer(config)


    @staticmethod
    def _fail_fast(err, msg):
        if err is not None:
            print("Kafka producer delivery error: {}".format(err), file=sys.stderr)
            print("Bailing out...", file=sys.stderr)
            # TODO: should it be sys.exit(-1)?
            raise KafkaException(err)

    def producer_config(self, kafka_config):
        config = kafka_config.copy()
        config.update({
            'delivery.report.only.error': True,
            'default.topic.config': {
                'message.timeout.ms': 30000,
                'request.required.acks': -1, # all brokers must confirm
            }
        })
        return config

    def push_record(self, msg, key=None):
        self.counts['total'] += 1
        if type(msg) == dict:
            if not key and 'key' in msg:
                key = msg['key']
            msg = json.dumps(msg)
        if type(msg) == str:
            msg = msg.encode('utf-8')
        assert type(msg) == bytes

        self.producer.produce(
            self.produce_topic,
            msg,
            key=key,
            on_delivery=self._fail_fast)
        self.counts['produced'] += 1

        # check for errors etc
        self.producer.poll(0)

    def push_batch(self, msgs):
        for m in msgs:
            self.push_record(m)

    def finish(self):
        self.producer.flush()
        return self.counts


class KafkaGrobidSink(KafkaSink):
    """
    Variant of KafkaSink for large documents. Used for, eg, GROBID output.
    """

    def producer_config(self, kafka_config):
        config = kafka_config.copy()
        config.update({
            'compression.codec': 'gzip',
            'retry.backoff.ms': 250,
            'linger.ms': 1000,
            'batch.num.messages': 50,
            'delivery.report.only.error': True,
            'default.topic.config': {
                'message.timeout.ms': 30000,
                'request.required.acks': -1, # all brokers must confirm
            }
        })
        return config


class RecordPusher:
    """
    Base class for different record sources to be pushed into workers. Pretty
    trivial interface, just wraps an importer and pushes records in to it.
    """

    def __init__(self, worker, **kwargs):
        self.counts = Counter()
        self.worker = worker

    def run(self):
        """
        This will look something like:

            for line in sys.stdin:
                record = json.loads(line)
                self.worker.push_record(record)
            print(self.worker.finish())
        """
        raise NotImplementedError


class JsonLinePusher(RecordPusher):

    def __init__(self, worker, json_file, **kwargs):
        self.counts = Counter()
        self.worker = worker
        self.json_file = json_file
        self.batch_size = kwargs.get('batch_size', None)
        if self.batch_size in (0, 1):
            self.batch_size = None

    def run(self):
        batch = []
        for line in self.json_file:
            if not line:
                continue
            self.counts['total'] += 1
            try:
                record = json.loads(line)
            except json.decoder.JSONDecodeError:
                self.counts['error-json-decode'] += 1
                continue
            if self.batch_size:
                batch.append(record)
                if len(batch) >= self.batch_size:
                    self.worker.push_batch(batch)
                    self.counts['pushed'] += len(batch)
                    batch = []
            else:
                self.worker.push_record(record)
                self.counts['pushed'] += 1
        if self.batch_size and batch:
            self.worker.push_batch(batch)
            self.counts['pushed'] += len(batch)
            batch = []
        worker_counts = self.worker.finish()
        print("JSON lines pushed: {}".format(self.counts), file=sys.stderr)
        return self.counts


class CdxLinePusher(RecordPusher):

    def __init__(self, worker, cdx_file, **kwargs):
        self.counts = Counter()
        self.worker = worker
        self.cdx_file = cdx_file
        self.filter_http_statuses = kwargs.get('filter_http_statuses', None)
        self.filter_mimetypes = kwargs.get('filter_mimetypes', None)
        self.allow_octet_stream = kwargs.get('allow_octet_stream', False)
        self.batch_size = kwargs.get('batch_size', None)
        if self.batch_size in (0, 1):
            self.batch_size = None

    def run(self):
        batch = []
        for line in self.cdx_file:
            if not line:
                continue
            self.counts['total'] += 1
            record = parse_cdx_line(line, normalize=True)
            if not record:
                self.counts['skip-parse'] += 1
                continue
            if self.filter_http_statuses and record['http_status'] not in self.filter_http_statuses:
                self.counts['skip-http_status'] += 1
                continue
            if self.filter_mimetypes and record['mimetype'] not in self.filter_mimetypes:
                self.counts['skip-mimetype'] += 1
                continue
            if self.batch_size:
                batch.append(record)
                if len(batch) >= self.batch_size:
                    self.worker.push_batch(batch)
                    self.counts['pushed'] += len(batch)
                    batch = []
            else:
                self.worker.push_record(record)
                self.counts['pushed'] += 1
        if self.batch_size and batch:
            self.worker.push_batch(batch)
            self.counts['pushed'] += len(batch)
            batch = []
        worker_counts = self.worker.finish()
        print("CDX lines pushed: {}".format(self.counts), file=sys.stderr)
        return self.counts


class ZipfilePusher(RecordPusher):

    def __init__(self, worker, zipfile_path, **kwargs):
        self.counts = Counter()
        self.worker = worker
        self.filter_suffix = ".pdf"
        self.zipfile_path = zipfile_path
        self.batch_size = kwargs.get('batch_size', None)
        if self.batch_size in (0, 1):
            self.batch_size = None

    def run(self):
        batch = []
        with zipfile.ZipFile(self.zipfile_path, 'r') as archive:
            for zipinfo in archive.infolist():
                if not zipinfo.filename.endswith(self.filter_suffix):
                    continue
                self.counts['total'] += 1
                # NB doesn't really extract the file, just gives you a stream (file-like-object) for reading it
                flo = archive.open(zipinfo, 'r')
                data = flo.read(2**32)
                flo.close()
                if self.batch_size:
                    batch.append(data)
                    if len(batch) >= self.batch_size:
                        self.worker.push_batch(batch)
                        self.counts['pushed'] += len(batch)
                        batch = []
                else:
                    self.worker.push_record(data)
                    self.counts['pushed'] += 1
        if self.batch_size and batch:
            self.worker.push_batch(batch)
            self.counts['pushed'] += len(batch)
            batch = []
        worker_counts = self.worker.finish()
        print("ZIP PDFs pushed: {}".format(self.counts), file=sys.stderr)
        return self.counts

class KafkaJsonPusher(RecordPusher):

    def __init__(self, worker, kafka_hosts, consume_topic, group, **kwargs):
        self.counts = Counter()
        self.worker = worker
        self.consumer = make_kafka_consumer(
            kafka_hosts,
            consume_topic,
            group,
        )
        self.push_batches = kwargs.get('push_batches', False)
        self.poll_interval = kwargs.get('poll_interval', 5.0)
        self.batch_size = kwargs.get('batch_size', 100)
        if self.batch_size in (0, 1):
            self.batch_size = 1
        self.batch_worker = kwargs.get('batch_worker', False)

    def run(self):
        while True:
            # TODO: this is batch-oriented, because underlying worker is
            # often batch-oriented, but this doesn't confirm that entire batch
            # has been pushed to fatcat before commiting offset. Eg, consider
            # case where there there is one update and thousands of creates;
            # update would be lingering in worker, and if worker crashed
            # never created. Not great.
            batch = self.consumer.consume(
                num_messages=self.batch_size,
                timeout=self.poll_interval)
            print("... got {} kafka messages ({}sec poll interval)".format(
                    len(batch), self.poll_interval),
                file=sys.stderr)
            if not batch:
                # TODO: could have some larger timeout here and
                # self.worker.finish() if it's been more than, eg, a couple
                # minutes
                continue
            # first check errors on entire batch...
            for msg in batch:
                if msg.error():
                    raise KafkaException(msg.error())
            # ... then process
            if self.push_batches:
                self.counts['total'] += len(batch)
                records = [json.loads(msg.value().decode('utf-8')) for msg in batch]
                self.worker.push_batch(records)
                self.counts['pushed'] += len(batch)
                print("Import counts: {}".format(self.worker.counts), file=sys.stderr)
            else:
                for msg in batch:
                    self.counts['total'] += 1
                    record = json.loads(msg.value().decode('utf-8'))
                    # This complex bit of code implements backoff/backpressure
                    # in a way that will not cause this Kafka consumer to lose
                    # partition assignments (resulting in a rebalance). This
                    # was needed for the ingest workers. There is probably a
                    # better way to structure this concurrency.
                    done = False
                    while not done:
                        try:
                            # use timeouts; don't want kafka itself to timeout
                            self.worker.push_record_timeout(record, timeout=300)
                            break
                        except SandcrawlerBackoffError as be:
                            print("Backing off for 200 seconds: {}".format(be))
                            self.consumer.pause(self.consumer.assignment())
                            for i in range(40):
                                # Beware this poll which should not be
                                # receiving any messages because we are paused!
                                empty_batch = self.consumer.poll(0)
                                assert not empty_batch
                                time.sleep(5)
                            self.consumer.resume(self.consumer.assignment())
                    self.counts['pushed'] += 1
                    if self.counts['total'] % 500 == 0:
                        print("Import counts: {}".format(self.worker.counts), file=sys.stderr)
            for msg in batch:
                # locally store offsets of processed messages; will be
                # auto-commited by librdkafka from this "stored" value
                self.consumer.store_offsets(message=msg)

        # TODO: should catch UNIX signals (HUP?) to shutdown cleanly, and/or
        # commit the current batch if it has been lingering
        worker_counts = self.worker.finish()
        print("KafkaJson lines pushed: {}".format(self.counts), file=sys.stderr)
        self.consumer.close()
        return self.counts


def make_kafka_consumer(hosts, consume_topic, group):
    topic_name = consume_topic

    def fail_fast(err, partitions):
        if err is not None:
            print("Kafka consumer commit error: {}".format(err), file=sys.stderr)
            print("Bailing out...", file=sys.stderr)
            # TODO: should it be sys.exit(-1)?
            raise KafkaException(err)
        for p in partitions:
            # check for partition-specific commit errors
            if p.error:
                print("Kafka consumer commit error: {}".format(p.error), file=sys.stderr)
                print("Bailing out...", file=sys.stderr)
                # TODO: should it be sys.exit(-1)?
                raise KafkaException(p.error)
        #print("Kafka consumer commit successful")
        pass

    # previously, using pykafka
    #auto_commit_enable=True,
    #auto_commit_interval_ms=30000, # 30 seconds
    conf = {
        'bootstrap.servers': hosts,
        'group.id': group,
        'on_commit': fail_fast,
        # messages don't have offset marked as stored until processed,
        # but we do auto-commit stored offsets to broker
        'enable.auto.offset.store': False,
        'enable.auto.commit': True,
        # user code timeout; if no poll after this long, assume user code
        # hung and rebalance (default: 6min)
        'max.poll.interval.ms': 360000,
        'default.topic.config': {
            'auto.offset.reset': 'latest',
        },
    }

    def on_rebalance(consumer, partitions):
        for p in partitions:
            if p.error:
                raise KafkaException(p.error)
        print("Kafka partitions rebalanced: {} / {}".format(
                consumer, partitions),
            file=sys.stderr)

    consumer = Consumer(conf)
    # NOTE: it's actually important that topic_name *not* be bytes (UTF-8
    # encoded)
    consumer.subscribe([topic_name],
        on_assign=on_rebalance,
        on_revoke=on_rebalance,
    )
    print("Consuming from kafka topic {}, group {}".format(topic_name, group), file=sys.stderr)
    return consumer
