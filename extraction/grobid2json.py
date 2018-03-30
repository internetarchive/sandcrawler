#!/usr/bin/env python3

"""
This script tries to extract everything from a GROBID TEI XML fulltext dump:

- header metadata
- affiliations
- references (with context)
- abstract
- fulltext
- tables, figures, equations

A flag can be specified to disable copyright encumbered bits (--no-emcumbered):

- abstract
- fulltext
- tables, figures, equations

Prints JSON to stdout, errors to stderr
"""

import os
import sys
import json
import argparse
import xml.etree.ElementTree as ET

ns = "http://www.tei-c.org/ns/1.0"

def all_authors(elem):
    names = [' '.join([e.findtext('./{%s}forename' % ns) or '', e.findtext('./{%s}surname' % ns) or '']).strip()
            for e in elem.findall('.//{%s}author/{%s}persName' % (ns, ns))]
    return [dict(name=n) for n in names]


def journal_info(elem):
    journal = dict()
    journal['name'] = elem.findtext('.//{%s}monogr/{%s}title' % (ns, ns))
    journal['publisher'] = elem.findtext('.//{%s}publicationStmt/{%s}publisher' % (ns, ns))
    journal['issn'] = elem.findtext('.//{%s}idno[@type="ISSN"]' % ns)
    journal['eissn'] = elem.findtext('.//{%s}idno[@type="eISSN"]' % ns)
    journal['volume'] = elem.findtext('.//{%s}biblScope[@unit="volume"]' % ns)
    journal['issue'] = elem.findtext('.//{%s}biblScope[@unit="issue"]' % ns)
    return journal


def biblio_info(elem):
    ref = dict()
    ref['id'] = elem.attrib.get('{http://www.w3.org/XML/1998/namespace}id')
    # Title stuff is messy in references...
    ref['title'] = elem.findtext('.//{%s}analytic/{%s}title' % (ns, ns))
    other_title = elem.findtext('.//{%s}monogr/{%s}title' % (ns, ns))
    if other_title:
        if ref['title']:
            ref['journal'] = other_title
        else:
            ref['journal'] = None
            ref['title'] = other_title
    ref['authors'] = all_authors(elem)
    ref['publisher'] = elem.findtext('.//{%s}publicationStmt/{%s}publisher' % (ns, ns))
    date = elem.find('.//{%s}date[@type="published"]' % ns)
    ref['date'] = (date != None) and date.attrib.get('when')
    ref['volume'] = elem.findtext('.//{%s}biblScope[@unit="volume"]' % ns)
    ref['issue'] = elem.findtext('.//{%s}biblScope[@unit="issue"]' % ns)
    el = elem.find('.//{%s}ptr[@target]' % ns)
    if el is not None:
        ref['url'] = el.attrib['target']
        # Hand correction
        if ref['url'].endswith(".Lastaccessed"):
            ref['url'] = ref['url'].replace(".Lastaccessed", "")
    else:
        ref['url'] = None
    return ref


def do_tei(path, encumbered=True):

    info = dict(filename=os.path.basename(path))

    tree = ET.parse(path)
    tei = tree.getroot()

    header = tei.find('.//{%s}teiHeader' % ns)
    info['title'] = header.findtext('.//{%s}analytic/{%s}title' % (ns, ns))
    info['authors'] = all_authors(header.find('.//{%s}sourceDesc/{%s}biblStruct' % (ns, ns)))
    info['journal'] = journal_info(header)
    date = header.find('.//{%s}date[@type="published"]' % ns)
    info['date'] = (date != None) and date.attrib.get('when')
    info['doi'] = header.findtext('.//{%s}idno[@type="DOI"]' % ns)
    if info['doi']:
        info['doi'] = info['doi'].lower()

    refs = []
    for (i, bs) in enumerate(tei.findall('.//{%s}listBibl/{%s}biblStruct' % (ns, ns))):
        ref = biblio_info(bs)
        ref['index'] = i
        refs.append(ref)
    info['citations'] = refs

    if encumbered:
        el = tei.find('.//{%s}profileDesc/{%s}abstract' % (ns, ns))
        info['abstract'] = (el or None) and " ".join(el.itertext()).strip()
        el = tei.find('.//{%s}text/{%s}body' % (ns, ns))
        info['body'] = (el or None) and " ".join(el.itertext()).strip()
        el = tei.find('.//{%s}back/{%s}div[@type="acknowledgement"]' % (ns, ns))
        info['acknowledgement'] = (el or None) and " ".join(el.itertext()).strip()
        el = tei.find('.//{%s}back/{%s}div[@type="annex"]' % (ns, ns))
        info['annex'] = (el or None) and " ".join(el.itertext()).strip()

    return info    

def main():
    parser = argparse.ArgumentParser(
        description="GROBID TEI XML to JSON",
        usage="%(prog)s [options] <teifile>...")
    parser.add_argument("--no-encumbered",
        action="store_true",
        help="ignore errors loading individual WARC files")
    parser.add_argument("teifiles", nargs='+')

    args = parser.parse_args()

    for filename in args.teifiles:
        print(json.dumps(
            do_tei(filename,
               encumbered=(not args.no_encumbered))))

if __name__=='__main__':
    main()
