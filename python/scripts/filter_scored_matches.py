#!/usr/bin/env python3
"""
Filters an input stream of sorted "matchcrossref" scalding job, and outputs
"good enough" matches to be inserted to fatcat.

Currently works on DOI numbers. Filters for a high enough string match (doesn't
re-do title match), and checks author lists. Filters out slugs with too many
matches, and outputs one-line-per-sha1 (aka, file).

No dependencies (only python3 stdlib)
"""

import json
import sys

# out of 1000
score_threshold = 900

max_slug_lines = 10

require_authors = 1


def tokenize(s, remove_whitespace=False):

    s.replace('&apos;', "'")
    # Remove non-alphanumeric characters
    s = ''.join([c for c in s.lower() if c.isalnum() or c.isspace()])

    if remove_whitespace:
        s = ''.join(s.split())

    # Encode as dumb ASCII (TODO: this is horrible)
    return s.encode('ascii', 'replace').replace(b'?', b'')


def check_authors(left, right):
    """
    Intended to check GROBID extracted authors (right) against "known good"
    (but maybe not perfect) Crossref metadata authors ("left").
    """
    if not left:
        return False
    if len(left) > len(right):
        return False
    right_all = tokenize(" ".join(right))
    for i in range(len(left)):
        l = left[i].lower().replace('jr.', '').split()
        if not l:
            return False
        l = tokenize(l[-1])
        if len(l) <= 1:
            # weird author name (single char)
            return False
        if l not in right_all:
            #print("MISSING: {} from {}".format(l.decode('utf8'), right_all.decode('utf8')))
            return False
    return True


def test_check_authors():
    assert not check_authors([], [])
    assert not check_authors([], ['one'])
    assert check_authors(['one'], ['one'])
    assert check_authors(['one two'], ['One Two'])
    assert check_authors(['two'], ['One Two'])
    assert check_authors(['two'], ['two, one'])
    assert check_authors(['mago'], ['Mr. Magoo'])
    assert check_authors(['Mr. Magoo'], ['Mr Magoo'])
    assert check_authors(['one', 'tw', 'thr'], ['one', 'two', 'three'])


# Rows are (score, grobid, crossref)
def process_group(rows):
    if len(rows) > max_slug_lines:
        return
    keepers = dict()
    for row in rows:
        score = int(row[0])
        if score < score_threshold:
            continue
        grobid = json.loads(row[1])
        crossref = json.loads(row[2])
        if not check_authors(crossref['authors'], grobid['authors']):
            #print("NO (crossref/grobid): {} {}".format(crossref['authors'], grobid['authors']))
            continue
        else:
            #print("YES: {} {}".format(crossref['authors'], grobid['authors']))
            pass
        sha1 = grobid['sha1']
        doi = crossref['doi'].lower()
        l = keepers.get(sha1, list())
        l.append(doi)
        keepers[sha1] = l
    for sha1, doi_list in keepers.items():
        print("{}\t{}".format(sha1, json.dumps(doi_list)))


def run():

    last_slug = None
    lines = []

    # group lines by slug, and process in batches
    for line in sys.stdin:
        line = line.strip().split('\t')
        assert len(line) == 4
        slug = line[0]
        if last_slug and slug != last_slug and lines:
            process_group(lines)
            lines = []
        last_slug = slug
        lines.append(line[1:])

    # catch any remaining
    if lines:
        process_group(lines)


if __name__ == '__main__':
    run()
