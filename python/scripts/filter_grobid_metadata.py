#!/usr/bin/env python3

import json
import sys

with open('title_slug_denylist.txt', 'r') as f:
    TITLE_DENYLIST = [l.strip() for l in f]

TITLE_DENYLIST.extend((
    'editorial',
    'advertisement',
    'bookreviews',
    'reviews',
    'nr',
    'abstractoriginalarticle',
    'originalarticle',
    'impactfactor',
    'articlenumber',
))

# The full name can't *entirely* be one of these
NAME_DENYLIST = (
    'phd',
    'phdstudent',
)

def tokenize(s, remove_whitespace=True):

    s.replace('&apos;', "'")
    # Remove non-alphanumeric characters
    s = ''.join([c for c in s.lower() if c.isalpha() or c.isspace()])

    if remove_whitespace:
        s = ''.join(s.split())

    # Encode as dumb ASCII (TODO: this is horrible)
    return s.encode('ascii', 'replace').decode('utf8').replace('?', '')

assert tokenize("Impact Factor: 2.114") == "impactfactor"
assert tokenize("Impact Factor: 2.114") in TITLE_DENYLIST

def filter_title(title):

    title = title.strip()
    if len(title) > 500:
        return None
    title_slug = tokenize(title, remove_whitespace=True)
    if len(title_slug) < 10 or title_slug in TITLE_DENYLIST:
        return None
    if title_slug.startswith('nr'):
        return None
    if title.lower().replace('.', '').startswith('int j '):
        return None

    for prefix in ("Title: ", "Original Article: ", "Article: ", "Original Article "):
        if title.startswith(prefix):
            title.replace(prefix, '')

    if title.startswith("The Journal of "):
        return None

    if "volume" in title_slug and "issue" in title_slug:
        return None

    if "downloadedfrom" in title_slug:
        return None

    if title_slug.startswith("issn"):
        return None

    # titles with too many or too few words in title
    title_words = len(title.split())
    if title_words > 50 or title_words < 2:
        return None

    # titles with spaces between every letter (more than N such single-char words)
    if len([True for w in title.split() if len(w) == 1]) > 12:
        return None

    # too deep subtitling/splitting
    if title.count(':') > 3 or title.count('|') > 1 or title.count('.') > 1:
        return None

    return title

def filter_author_name(name):
    name = name['name']
    if name.strip().lower().replace(' ', '') in NAME_DENYLIST:
        return None
    return ' '.join([t for t in name.split() if tokenize(t)])

def filter_authors(l):
    return [dict(name=n) for n in map(filter_author_name, l) if n and len(n) > 1]

def filter_refs(l):
    # TODO:
    return l

def filter_journal_name(name):
    # same denylist, for now
    if not name:
        return None
    name = name.replace(' e-ISSN', '').replace(' p-ISSN', '')
    slug_name = tokenize(name)
    if slug_name in TITLE_DENYLIST or len(slug_name) < 4 or name == "N.º":
        return None
    for prefix in ("/ ", "~ ", "& ", "© ", "Original Research Article ", "Original Article ", "Research Article ", "Available online www.jocpr.com "):
        if name.startswith(prefix):
            name = name.replace(prefix, '')
    for suffix in (" Available online at www.sciarena.com", " Original Article", " Available online at", " ISSN", " ISSUE"):
        if name.endswith(suffix):
            name = name.replace(suffix, '')
    if "====================" in name:
        return None
    if len(name) > 150:
        return None
    return ' '.join(name.split())

def filter_metadata(obj):
    if not (obj.get('title') and obj.get('authors')):
        return None

    title = filter_title(obj['title'])
    if not title:
        #sys.stderr.write("bad title\n")
        return None
    else:
        obj['title'] = title
    obj['authors'] = filter_authors(obj['authors'])
    obj['citations'] = filter_refs(obj['citations'])
    obj['journal']['name'] = filter_journal_name(obj['journal']['name'])

    return obj

def run(invert=False):
    for line in sys.stdin:
        fields = line.split('\t')
        if len(fields) == 5:
            raw = fields[4]
        elif len(fields) == 1:
            raw = fields[0]
        else:
            sys.stderr.write("bad line\n")
            continue
        obj = json.loads(raw)
        processed = filter_metadata(obj)
        if processed:
            if not invert:
                processed = json.dumps(processed)
                if len(fields) == 5:
                    fields[4] = processed
                else:
                    fields[0] = processed
                print('\t'.join(fields))
        elif invert:
            print(raw.strip())

if __name__=="__main__":
    run(invert="--invert" in sys.argv)
