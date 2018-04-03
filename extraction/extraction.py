#!/usr/bin/env python3

import io
import sys
import requests
#import happybase
import mrjob
from mrjob.job import MRJob
from wayback.resource import Resource
from wayback.resource import ArcResource
from wayback.resourcestore import ResourceStore
from gwb.loader import CDXLoaderFactory


def process_pdf_using_grobid(content_buffer, debug_line):
    """Query GrobId server & process response
    """
    GROBID_SERVER="http://wbgrp-svc096.us.archive.org:8070"
    content = content_buffer.read()
    r = requests.post(GROBID_SERVER + "/api/processFulltextDocument",
            files={'input': content})
    if r.status_code is not 200:
        print("FAIL (Grobid: {}): {}".format(r.content.decode('utf8'), debug_line))
    else:
        print("SUCCESS: " + debug_line)

class Cdx_Record_Pipeline(object):

    def read_cdx_and_parse(self, parser_func, accepted_mimes = []):
        """Read in CDX lines and process PDF records fetched over HTTP
        """
        rstore = ResourceStore(loaderfactory=CDXLoaderFactory()) 
        for line in sys.stdin:
            line = line.rstrip()
            cdx_line = line.split()
            #ignoring NLine offset
            if len(cdx_line) != 12:
                continue
            cdx_line = cdx_line[1:]
            (src_url, timestamp, mime, record_location, record_offset, record_length) = (cdx_line[2], cdx_line[1], cdx_line[3], cdx_line[-1], cdx_line[-2], cdx_line[-3])
            if '-' == record_length or not record_location.endswith('arc.gz') or mime not in accepted_mimes:
                continue
            orig_url = cdx_line[2]
            debug_line = ' '.join(cdx_line)
            try:
                record_location = 'http://archive.org/download/' + record_location
                record_offset = int(record_offset)
                record_length = int(record_length)
                resource_data = rstore.load_resource(record_location, record_offset, record_length)
                parser_func(resource_data.open_raw_content(), debug_line)
            except:
                continue
