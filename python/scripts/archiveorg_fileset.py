#!/usr/bin/env python3
"""
Helper script to 

Takes either two args (release ident and archive.org item), or a stream of
tab-separated such pairs on stdin.

TODO:
- should this check the item type?
"""

import sys
import json
from typing import Any

import internetarchive


FORMAT_TO_MIMETYPE = {
    'BZIP': 'application/x-bzip',
    'BZIP2': 'application/x-bzip2',
    'ZIP': 'application/zip',
    'GZIP': 'application/gzip',
    'RAR': 'application/vnd.rar',
    'TAR': 'application/x-tar',
    '7z': 'application/x-7z-compressed',

    'HTML': 'text/html',
    'Text': 'text/plain',
    'PDF': 'application/pdf',

    'CSV': 'text/csv',
    'XML': 'application/xml',
    'JSON': 'application/json',

    #'application/msword (.doc)', # .doc
    #'application/vnd.openxmlformats-officedocument.wordprocessingml.document', # .docx
    #'application/vnd.ms-excel', # .xls
    #'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', # .xlsx

    'MP3': 'audio/mpeg', # .mp3

    'MP4': 'video/mp4', # .mp4
    'MPEG': 'video/mpeg', # .mpeg

    'JPEG': 'image/jpeg',
    'GIF': 'image/gif',
    'PNG': 'image/png',
    'TIFF': 'image/tiff',

    'Unknown': None,
}

def want_file(f: dict, item_name: str) -> bool:
    """
    Filters IA API files
    """
    if f.source != 'original':
        return False
    for suffix in [
        '_meta.sqlite',
        '_archive.torrent',
        '_itemimage.jpg',
        '_meta.xml',
        '_thumb.png',
        '_files.xml',
    ]:
        if f.name == item_name + suffix or f.name == item_name.lower() + suffix:
            return False
    if f.name.startswith('_'):
        return False
    if item_name.startswith('academictorrents_'):
        for suffix in ['_academictorrents.torrent', '_academictorrents_torrent.txt', '.bib']:
            if f.name == item_name + suffix:
                return False
    return True

def parse_file(f: dict) -> dict:
    """
    Takes an IA API file and turns it in to a fatcat fileset manifest file
    """
    assert f.name and f.sha1 and f.md5
    assert f.name is not None
    mf = {
        'path': f.name,
        'size': int(f.size),
        'sha1': f.sha1,
        'md5': f.md5,
    }
    # TODO: will disable this hard check eventually and replace with:
    #mimetype = FORMAT_TO_MIMETYPE.get(f.format)
    mimetype = FORMAT_TO_MIMETYPE[f.format]
    if mimetype:
        mf['extra'] = dict(mimetype=mimetype)
    return mf

def item_to_fileset(item_name: str, release_id: str, session: internetarchive.ArchiveSession):
    print(f"processing item={item_name} release_id={release_id}", file=sys.stderr)
    if release_id.startswith('release_'):
        release_id = release_id[9:]
    assert len(release_id) == 26
    item = session.get_item(item_name)
    assert item.metadata['mediatype'] not in ['collection', 'web']
    item_files = item.get_files(on_the_fly=False)
    manifest = [parse_file(f) for f in item_files if want_file(f, item_name)]
    fileset = {
        'manifest': manifest,
        'urls': [
            {
                'rel': 'archive',
                'url': f'https://archive.org/download/{item_name}/',
            },
        ],
        'release_ids': [release_id],
        #extra={},
    }
    print(json.dumps(fileset))
    return fileset

def main():
    session = internetarchive.get_session()
    if len(sys.argv) == 3:
        item_name = sys.argv[1]
        release_id = sys.argv[2]
        item_to_fileset(item_name, release_id=release_id, session=session)
    else:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            fields = line.split('\t')
            assert len(fields) == 2
            item_name = fields[0]
            release_id = fields[1]
            item_to_fileset(item_name, release_id=release_id, session=session)

if __name__ == '__main__':
    main()
