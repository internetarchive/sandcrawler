#!/usr/bin/env python3

"""
Takes old (HBase) or new (pg) style JSON wrappers of GROBID XML extraction
output, converts the XML to JSON, filters out raw affiliation strings, and
dumps these as JSON subset.

Run in bulk like:

    ls /bigger/unpaywall-transfer/2019-07-17-1741.30-dumpgrobidxml/part*gz | parallel --progress -j8 'zcat {} | ./grobid_affiliations.py > {}.affiliations'
"""

import sys
import json

from grobid2json import teixml2json

def parse_hbase(line):
    line = line.split('\t')
    assert len(line) == 2
    sha1hex = line[0]
    obj = json.loads(line[1])
    tei_xml = obj['tei_xml']
    return sha1hex, tei_xml

def parse_pg(line):
    obj = json.loads(line)
    return obj['sha1hex'], obj['tei_xml']

def run(mode='hbase'):
    for line in sys.stdin:
        if mode == 'hbase':
            sha1hex, tei_xml = parse_hbase(line)
        elif mode == 'pg':
            sha1hex, tei_xml = parse_pg(line)
        else:
            raise NotImplementedError('parse mode: {}'.format(mode))

        obj = teixml2json(tei_xml, encumbered=False)

        affiliations = []
        for author in obj['authors']:
            if author.get('affiliation'):
                affiliations.append(author['affiliation'])
        if affiliations:
            # don't duplicate affiliations; only the unique ones
            affiliations = list(set([json.dumps(a) for a in affiliations]))
            affiliations = [json.loads(a) for a in affiliations]
            print('\t'.join([sha1hex, json.dumps(affiliations)]))

if __name__=='__main__':
    run()
