#!/usr/bin/env python3

"""
Input is IA item metadata JSON.
Ouput is insertable fatcat "match" JSON

- md5
- sha1
- sha256
- size
- urls
- cdx (list; empty here)

- dois (list)
- pmcid
- jstor
- arxiv

When invoking import matched, be sure to:

    --default-link-rel repository (?)
    --default-mimetype application/pdf
"""

import sys
import json

def parse(obj):
    if obj['metadata']['identifier'].endswith('-test') or obj['metadata'].get('test'):
        print('skip: test item', file=sys.stderr)
        return None

    extid_type = None
    extid = None
    if obj['metadata']['identifier'].startswith('arxiv-'):
        extid_type = 'arxiv'
        extid = obj['metadata'].get('source')
        if not extid:
            print('skip: no source', file=sys.stderr)
            return None
        assert extid.startswith('http://arxiv.org/abs/')
        extid = extid.replace('http://arxiv.org/abs/', '')
        #print(extid)
        assert '/' in extid or '.' in extid
        if not 'v' in extid or not extid[-1].isdigit():
            print('skip: non-versioned arxiv_id', file=sys.stderr)
            return None
    elif obj['metadata']['identifier'].startswith('paper-doi-10_'):
        extid_type = 'doi'
        extid = obj['metadata']['identifier-doi']
        assert extid.startswith("10.")
    elif obj['metadata']['identifier'].startswith('pubmed-PMC'):
        extid_type = 'pmcid'
        extid = obj['metadata']['identifier'].replace('pubmed-', '')
        assert extid.startswith("PMC")
        int(extid[3:])
    elif obj['metadata']['identifier'].startswith('jstor-'):
        extid_type = 'jstor'
        extid = obj['metadata']['identifier'].replace('jstor-', '')
        int(extid)
    else:
        raise NotImplementedError()

    pdf_file = None
    for f in obj['files']:
        if f['source'] == "original" and "PDF" in f['format']:
            pdf_file = f
            break
    if not pdf_file:
        print('skip: no PDF found: {}'.format(obj['metadata']['identifier']), file=sys.stderr)
        #for f in obj['files']:
        #    print(f['format'], file=sys.stderr)
        return None

    assert pdf_file['name'].endswith('.pdf')

    match = {
        'md5': pdf_file['md5'],
        'sha1': pdf_file['sha1'],
        'size': int(pdf_file['size']),
        'mimetype': 'application/pdf',
        'urls': [
            "https://archive.org/download/{}/{}".format(
                obj['metadata']['identifier'],
                pdf_file['name']),
        ],
        'cdx': [],
        'dois': [],
    }

    if extid_type == 'doi':
        match['dois'] = [extid,]
    else:
        match[extid_type] = extid

    return match

def run():
    for line in sys.stdin:
        if not line:
            continue
        obj = json.loads(line)
        match = parse(obj)
        if match:
            print(json.dumps(match, sort_keys=True))

if __name__ == '__main__':
    run()
