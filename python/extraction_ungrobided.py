#!/usr/bin/env python3
"""
Variant of extraction_cdx_grobid which takes a partial metadata list as input
instead of CDX. 

This task list is dumped by another Hadoop job which scans over the HBase table
quickly, which allows this job to skip a (relatively) expensive HBase read
per-row.

Requires:
- happybase
- mrjob
- wayback/GWB libraries
"""

# XXX: some broken MRO thing going on in here due to python3 object wrangling
# in `wayback` library. Means we can't run pylint.
# pylint: skip-file

import xml
import json
import raven
import struct
import mrjob
from common import parse_ungrobided_line
from extraction_cdx_grobid import MRExtractCdxGrobid, KEY_BLACKLIST, \
    sentry_client


class MRExtractUnGrobided(MRExtractCdxGrobid):

    # "ungrobided" TSV lines in; JSON status out
    #HADOOP_INPUT_FORMAT = 'org.apache.hadoop.mapred.lib.NLineInputFormat'
    #INPUT_PROTOCOL = mrjob.protocol.RawProtocol
    INPUT_PROTOCOL = mrjob.protocol.RawValueProtocol
    OUTPUT_PROTOCOL = mrjob.protocol.JSONValueProtocol

    def parse_ungrobided_line(self, raw_line):
        """Line should be TSV and have non-null fields:

            - key (string)
            - f:c (string, json)
            - file:mime (string)
            - file:cdx (string, json)
        """

        if (raw_line.startswith(' ') or raw_line.startswith('#')):
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

    @sentry_client.capture_exceptions
    def mapper(self, _, raw_line):
        """
        1. parse filtered line
        2. fetch data from wayback
        3. submit to GROBID
          4. convert GROBID response to JSON (and metadata)
          6. determine "quality"
        6. push results to hbase
        """

        self.increment_counter('lines', 'total')

        # Parse line and filter down
        info, status = self.parse_ungrobided_line(raw_line)
        if info is None:
            self.increment_counter('lines', status['status'])
            yield _, status
            return
        key = info['key']
        if key in KEY_BLACKLIST:
            self.increment_counter('lines', 'blacklist')
            yield _, dict(status='blacklist', key=key)
            return

        # Note: this may not get "cleared" correctly
        sentry_client.extra_context(dict(row_key=key))

        # Do the extraction
        info, status = self.extract(info)
        if info is None:
            self.increment_counter('lines', status['status'])
            status['key'] = key
            yield _, status
            return
        extraction_status = status

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
        self.increment_counter('lines', 'success')

        if extraction_status is not None:
            yield _, dict(status="partial", key=key,
                grobid_status_code=grobid_status_code,
                reason=extraction_status['reason'])
        else:
            yield _, dict(status="success",
                grobid_status_code=grobid_status_code, key=key,
                extra=extraction_status)


if __name__ == '__main__': # pragma: no cover
    MRExtractUnGrobided.run()
