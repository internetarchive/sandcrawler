#!/usr/bin/env python3
"""
Tool for bulk copying of PDFs (or other files) from GWB to local disk.
"""

# XXX: some broken MRO thing going on in here due to python3 object wrangling
# in `wayback` library. Means we can't run pylint.
# pylint: skip-file

import os
import sys
import json
import base64
import hashlib
import argparse
from collections import Counter

import raven
import wayback.exception
from http.client import IncompleteRead
from wayback.resourcestore import ResourceStore
from gwb.loader import CDXLoaderFactory

# Yep, a global. Gets DSN from `SENTRY_DSN` environment variable
sentry_client = raven.Client()


class DeliverGwbDisk:

    def __init__(self, disk_dir, **kwargs):
        self.warc_uri_prefix = kwargs.get('warc_uri_prefix')
        self.rstore = None
        self.count = Counter()
        # /serve/ instead of /download/ doesn't record view count
        self.petabox_base_url = kwargs.get('petabox_base_url', 'http://archive.org/serve/')
        # gwb library will fall back to reading from /opt/.petabox/webdata.secret
        self.petabox_webdata_secret = kwargs.get('petabox_webdata_secret', os.environ.get('PETABOX_WEBDATA_SECRET'))
        self.disk_dir = disk_dir
        self.disk_prefix = kwargs.get('disk_prefix', 'pdf/')
        self.disk_suffix = kwargs.get('disk_suffix', '.pdf')

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

    def run(self, manifest_file):
        sys.stderr.write("Ensuring all 65536 base directories exist...\n")
        for i in range(256):
            for j in range(256):
                fpath = "{}/{}{:02x}/{:02x}".format(
                        self.disk_dir,
                        self.disk_prefix,
                        i,
                        j)
                os.makedirs(fpath, exist_ok=True)
        sys.stderr.write("Starting...\n")
        for line in manifest_file:
            self.count['total'] += 1
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
            if blob is None and status:
                print("{}\terror petabox\t{}\t{}".format(sha1_hex, file_cdx['warc'], status['reason']))
                self.count['err-petabox-fetch'] += 1
                continue
            elif not blob:
                print("{}\tskip-empty-blob".format(sha1_hex))
                self.count['skip-empty-blob'] += 1
                continue
            # verify sha1
            if sha1_hex != hashlib.sha1(blob).hexdigest():
                #assert sha1_hex == hashlib.sha1(blob).hexdigest()
                #sys.stderr.write("{}\terror petabox-mismatch\n".format(sha1_hex))
                print("{}\terror petabox-hash-mismatch".format(sha1_hex))
                self.count['err-petabox-hash-mismatch'] += 1

            self.count['petabox-ok'] += 1
            # save to disk
            fpath = "{}/{}{}/{}/{}{}".format(
                    self.disk_dir,
                    self.disk_prefix,
                    sha1_hex[0:2],
                    sha1_hex[2:4],
                    sha1_hex,
                    self.disk_suffix)
            with open(fpath, 'wb') as f:
                f.write(blob)
            print("{}\tsuccess\t{}\t{}".format(sha1_hex, fpath, len(blob)))
            self.count['success-disk'] += 1
        sys.stderr.write("{}\n".format(self.count))

@sentry_client.capture_exceptions
def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--disk-dir',
                        required=True,
                        type=str,
                        help='local base directory to save into')
    parser.add_argument('--disk-prefix',
                        type=str,
                        default="pdf/",
                        help='directory prefix for items created in bucket')
    parser.add_argument('--disk-suffix',
                        type=str,
                        default=".pdf",
                        help='file suffix for created files')
    parser.add_argument('--warc-uri-prefix',
                        type=str,
                        default='https://archive.org/serve/',
                        help='URI where WARCs can be found')
    parser.add_argument('manifest_file',
                        help="TSV/JSON manifest file",
                        default=sys.stdin,
                        type=argparse.FileType('r'))
    args = parser.parse_args()

    worker = DeliverGwbDisk(**args.__dict__)
    worker.run(args.manifest_file)

if __name__ == '__main__': # pragma: no cover
    main()
