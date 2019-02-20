#!/usr/bin/env python3
"""
Tool for bulk copying of PDFs (or other files) from GWB to AWS S3.

Script should take:
- input TSV: `(sha1, datetime, terminal_url)` (can be exported from arabesque sqlite3 output)
    => sha1_hex, warc_path, offset, c_size
- GWB credentials
- AWS S3 bucket and prefix

AWS S3 credentials are passed via environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

GWB credentials end up under /opt/.petabox/ (!)

Output:
- errors/stats to stderr
- log to stdout (redirect to file), prefixed by sha1

Requires:
- wayback/GWB libraries
"""

import sys
import json
import base64
import hashlib
import argparse
from collections import Counter

import boto3
import raven
import wayback.exception
from wayback.resource import Resource
from wayback.resource import ArcResource
from wayback.resourcestore import ResourceStore
from gwb.loader import CDXLoaderFactory

# Yep, a global. Gets DSN from `SENTRY_DSN` environment variable
sentry_client = raven.Client()


class DeliverGwbS3():

    def __init__(self, s3_bucket, **kwargs):
        self.warc_uri_prefix = kwargs.get('warc_uri_prefix')
        self.mime_filter = ['application/pdf']
        self.rstore = None
        self.count = Counter()
        self.s3_bucket = s3_bucket
        self.s3_prefix = kwargs.get('s3_prefix', 'pdf/')
        self.s3_suffix = kwargs.get('s3_suffix', '.pdf')
        self.s3 = boto3.resource('s3')
        self.bucket = self.s3.Bucket(self.s3_bucket)

    def fetch_warc_content(self, warc_path, offset, c_size):
        warc_uri = self.warc_uri_prefix + warc_path
        if not self.rstore:
            self.rstore = ResourceStore(loaderfactory=CDXLoaderFactory())
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

    def run(self, manifest_file):
        sys.stderr.write("Starting...\n")
        for line in manifest_file:
            line = line.strip().split('\t')
            if len(line) != 2:
                self.count['skip-line'] += 1
                continue
            sha1_hex, cdx_json = line[0], line[1]
            assert len(sha1_hex) == 40
            file_cdx = json.loads(cdx_json)
            # If warc is not item/file.(w)arc.gz form, skip it
            if len(file_cdx['warc'].split('/')) != 2:
                sys.stderr.write('WARC path not petabox item/file: {}'.format(file_cdx['warc']))
                print("{}\tskip warc\t{}".format(sha1_hex, file_cdx['warc']))
                self.count['skip-warc'] += 1
                continue
            # fetch from GWB/petabox via HTTP range-request
            blob, status = self.fetch_warc_content(file_cdx['warc'], file_cdx['offset'], file_cdx['c_size'])
            if not blob:
                print("{}\terror petabox\t{}\t{}".format(sha1_hex, file_cdx['warc'], status['reason']))
                self.count['err-petabox'] += 1
                continue
            # verify sha1
            if sha1_hex != hashlib.sha1(blob).hexdigest():
                #assert sha1_hex == hashlib.sha1(blob).hexdigest()
                #sys.stderr.write("{}\terror petabox-mismatch\n".format(sha1_hex))
                print("{}\terror petabox-hash-mismatch".format(sha1_hex))
                self.count['petabox-hash-mismatch'] += 1

            self.count['petabox-ok'] += 1
            # upload to AWS S3
            obj = self.bucket.put_object(
                Key="{}{}/{}{}".format(
                    self.s3_prefix,
                    sha1_hex[0:4],
                    sha1_hex,
                    self.s3_suffix),
                Body=blob)
            print("{}\tsuccess\t{}".format(sha1_hex, obj.key))
            self.count['success-s3'] += 1
        sys.stderr.write("{}\n".format(self.count))

@sentry_client.capture_exceptions
def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--s3-bucket',
                        required=True,
                        type=str,
                        help='AWS S3 bucket to upload into')
    parser.add_argument('--s3-prefix',
                        type=str,
                        default="pdf/",
                        help='key prefix for items created in bucket')
    parser.add_argument('--s3-suffix',
                        type=str,
                        default=".pdf",
                        help='file suffix for created objects')
    parser.add_argument('--warc-uri-prefix',
                        type=str,
                        default='https://archive.org/serve/',
                        help='URI where WARCs can be found')
    parser.add_argument('manifest_file',
                        help="TSV/JSON manifest file",
                        default=sys.stdin,
                        type=argparse.FileType('r'))
    args = parser.parse_args()

    worker = DeliverGwbS3(**args.__dict__)
    worker.run(args.manifest_file)

if __name__ == '__main__': # pragma: no cover
    main()
