#!/usr/bin/env python3
"""
Filters an input stream of sorted "groupworks" scalding job, and outputs
"good enough" matches to be merged in fatcat.

Output is JSON lines which are arrays of releases that could/should be merged
together, either as multiple releases under a single work, or releases merged
into a single entity (via redirects).

Note that releases *should* only end up on a single line, and only once per
line!

No dependencies (only python3 stdlib)

Note: the actual importer/merger should filter the following patterns out:
- container title has "letter" and "diar"
- contribs (authors) contain "&NA;"
- dates differ (not just year)
"""

import sys
import json

# out of 1000
SCORE_THRESHOLD = 900

MAX_SLUG_LINES = 50

REQUIRE_AUTHORS = False

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
    if not left and not right:
        return bool(not REQUIRE_AUTHORS)
    if len(left) != len(right):
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
    assert check_authors([], []) == bool(not REQUIRE_AUTHORS)
    assert not check_authors([], ['one'])
    assert check_authors(['one'], ['one'])
    assert check_authors(['one two'], ['One Two'])
    assert check_authors(['two'], ['One Two'])
    assert check_authors(['two'], ['two, one'])
    assert check_authors(['mago'], ['Mr. Magoo'])
    assert check_authors(['Mr. Magoo'], ['Mr Magoo'])
    assert check_authors(['one', 'tw', 'thr'], ['one', 'two', 'three'])

# Rows are (score, left, right)
def process_group(rows):

    # first pass reduces size of list and generates a linkage graph
    filtered = list()
    for row in rows:
        score = int(row[0])
        if score < SCORE_THRESHOLD:
            continue
        left = json.loads(row[1])
        right = json.loads(row[2])
        # authors must roughly match
        if not check_authors(left['authors'], right['authors']):
            continue
        # years must match (if defined)
        if left['year'] and right['year'] and left['year'] != right['year']:
            continue
        filtered.append((left, right))

    if not filtered:
        return

    # second pass finds a connected graph and returns that
    releases = dict()
    group_ids = set()
    for row in filtered[1:]:
        (left, right) = row
        l_id = left['fatcat_release']
        r_id = right['fatcat_release']
        releases[l_id] = left
        releases[r_id] = right
        if not group_ids:
            group_ids.add(l_id)
            group_ids.add(r_id)
            continue
        if l_id in group_ids or r_id in group_ids:
            group_ids.add(l_id)
            group_ids.add(r_id)
            continue

    if not group_ids:
        return

    print(json.dumps([releases[ident] for ident in group_ids]))

def run():

    last_slug = None
    lines = []

    # group lines by slug, and process in batches
    for line in sys.stdin:
        line = line.strip().split('\t')
        assert len(line) == 4
        slug = line[0]
        if last_slug and slug != last_slug and lines:
            if len(lines) <= MAX_SLUG_LINES:
                process_group(lines)
            lines = []
        last_slug = slug
        lines.append(line[1:])

    # catch any remaining
    if lines:
        process_group(lines)

if __name__=='__main__':
    run()
