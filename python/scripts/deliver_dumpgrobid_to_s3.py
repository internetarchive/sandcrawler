#!/usr/bin/env python3
"""
Tool for bulk uploading GROBID TEI-XML output from a local filesystem dump
(from HBase) to AWS S3.

See unpaywall delivery README (in bnewbold's scratch repo) for notes on running
this script for that specific use-case.

Script takes:
- input TSV: `sha1_hex, json (including grobid0:tei_xml)`
    => usually from dumpgrobid, with SHA-1 key transformed to hex, and filtered
       down (eg, by join by SHA-1) to a specific manifest
- AWS S3 bucket and prefix

AWS S3 credentials are passed via environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

Output:
- errors/stats to stderr
- log to stdout (redirect to file), prefixed by sha1

Requires:
- raven (sentry)
- boto3 (AWS S3 client library)
"""

import os
import sys
import json
import base64
import hashlib
import argparse
from collections import Counter

import boto3
import raven

# Yep, a global. Gets DSN from `SENTRY_DSN` environment variable
sentry_client = raven.Client()


def b32_hex(s):
    """copy/pasta from elsewhere"""
    s = s.strip().split()[0].lower()
    if s.startswith("sha1:"):
        s = s[5:]
    if len(s) != 32:
        return s
    return base64.b16encode(base64.b32decode(s.upper())).lower().decode('utf-8')


class DeliverDumpGrobidS3():

    def __init__(self, s3_bucket, **kwargs):
        self.rstore = None
        self.count = Counter()
        self.s3_bucket = s3_bucket
        self.s3_prefix = kwargs.get('s3_prefix', 'grobid/')
        self.s3_suffix = kwargs.get('s3_suffix', '.tei.xml')
        self.s3_storage_class = kwargs.get('s3_storage_class', 'STANDARD')
        self.s3 = boto3.resource('s3')
        self.bucket = self.s3.Bucket(self.s3_bucket)

    def run(self, dump_file):
        sys.stderr.write("Starting...\n")
        for line in dump_file:
            line = line.strip().split('\t')
            if len(line) != 2:
                self.count['skip-line'] += 1
                continue
            sha1_hex, grobid_json = line[0], line[1]
            if len(sha1_hex) != 40:
                sha1_hex = b32_hex(sha1_hex)
            assert len(sha1_hex) == 40
            grobid = json.loads(grobid_json)
            tei_xml = grobid.get('tei_xml')
            if not tei_xml:
                print("{}\tskip empty".format(sha1_hex))
                self.count['skip-empty'] += 1
                continue
            tei_xml = tei_xml.encode('utf-8')
            # upload to AWS S3
            obj = self.bucket.put_object(
                Key="{}{}/{}{}".format(
                    self.s3_prefix,
                    sha1_hex[0:4],
                    sha1_hex,
                    self.s3_suffix),
                Body=tei_xml,
                StorageClass=self.s3_storage_class,
            )
            print("{}\tsuccess\t{}\t{}".format(sha1_hex, obj.key, len(tei_xml)))
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
                        default="grobid/",
                        help='key prefix for items created in bucket')
    parser.add_argument('--s3-suffix',
                        type=str,
                        default=".tei.xml",
                        help='file suffix for created objects')
    parser.add_argument('--s3-storage-class',
                        type=str,
                        default="STANDARD",
                        help='AWS S3 storage class (redundancy) to use')
    parser.add_argument('dump_file',
                        help="TSV/JSON dump file",
                        default=sys.stdin,
                        type=argparse.FileType('r'))
    args = parser.parse_args()

    worker = DeliverDumpGrobidS3(**args.__dict__)
    worker.run(args.dump_file)

if __name__ == '__main__': # pragma: no cover
    main()
