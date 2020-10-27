
import datetime
from typing import List, Optional, Any

import dateparser
from selectolax.parser import HTMLParser
import pydantic


# this is a map of metadata keys to CSS selectors
HEAD_META_PATTERNS: Any = {
    "title": [
        "meta[name='citation_title']",
        "meta[name='bepress_citation_title']",
        "meta[name='eprints.title']",
        "meta[name='prism.title']",
        "meta[name='dc.title']",
    ],
    "subtitle": [
        "meta[name='prism.subtitle']",
    ],
    "doi": [
        "meta[name='citation_doi']",
        "meta[name='prism.doi']",
        "meta[name='DOI']",
        "meta[id='DOI']",
        "meta[name='dc.identifier.doi']",
    ],
    "abstract": [
        "meta[name='citation_abstract']",
        "meta[name='dc.description']",
        "meta[name='og:description']",
    ],
    "container_name": [
        "meta[name='citation_journal_title']",
        "meta[name='citation_conference_title']",
        "meta[name='prism.publicationName']",
        "meta[name='dc.relation.ispartof']",
        "meta[name='dc.source']",
        "meta[property='og:site_name']",
    ],
    "container_abbrev": [
        "meta[name='citation_journal_abbrev']",
    ],
    "raw_date": [
        "meta[name='citation_publication_date']",
        "meta[name='citation_date']",
        "meta[name='prism.publicationDate']",
        "meta[itemprop='datePublished']",
        "meta[name='dc.date.created']",
        "meta[name='dc.issued']",
        "meta[name='dc.date']",
    ],
    "release_year": [
        "meta[itemprop='prism:copyrightYear']",
    ],
    "first_page": [
        "meta[name='citation_firstpage']",
        "meta[name='prism.startingPage']",
        "meta[name='dc.citation.spage']",
    ],
    "last_page": [
        "meta[name='citation_lastpage']",
        "meta[name='prism.endingPage']",
        "meta[name='dc.citation.epage']",
    ],
    "issue": [
        "meta[name='citation_issue']",
        "meta[name='prism.issueIdentifier']",
        "meta[name='dc.citation.issue']",
    ],
    "volume": [
        "meta[name='citation_volume']",
        "meta[name='prism.volume']",
        "meta[name='dc.citation.volume']",
    ],
    "number": [
        "meta[name='citation_technical_report_number']",
        "meta[name='citation_number']",
        "meta[name='prism.number']",
    ],
    "container_issn": [
        "meta[name='citation_issn']",
        "meta[name='prism.issn']",
        "meta[name='prism.eIssn']",
        "meta[name='dc.source.issn']",
    ],
    "isbn": [
        "meta[name='citation_isbn']",
        "meta[name='prism.isbn']",
    ],
    "publisher": [
        "meta[name='citation_publisher']",
        "meta[name='dc.publisher']",
    ],
    "raw_release_type": [
        "meta[name='citation_article_type']",
        "meta[name='prism.contentType']",
        "meta[name='dc.type']",
    ],
    "lang": [
        "meta[name='citation_language']",
        "meta[name='dc.language']",
    ],
    "html_fulltext_url": [
        "meta[name='citation_fulltext_html_url']",
    ],
    "xml_fulltext_url": [
    ],
    "pdf_fulltext_url": [
        "meta[name='citation_pdf_url']",
    ],
}

HEAD_META_LIST_PATTERNS: Any = {
    "contrib_names": [
        "meta[name='citation_author']",
        "meta[name='dc.creator']",
        "meta[name='dc.contributor']",
    ],
    # TODO: citation_author_institution
    "raw_references": [
        "meta[name='citation_reference']",
    ],
    "raw_identifiers": [
        "meta[name='dc.identifier']",
    ],
}

RELEASE_TYPE_MAP = {
    "research article": "article-journal",
    "text.serial.journal": "article-journal",
}


class BiblioMetadata(pydantic.BaseModel):
    title: Optional[str]
    subtitle: Optional[str]
    contrib_names: Optional[List[str]]
    release_date: Optional[datetime.date]
    release_year: Optional[int]
    release_type: Optional[str]
    release_stage: Optional[str]
    withdrawn_status: Optional[str]
    lang: Optional[str]
    country_code: Optional[str]
    volume: Optional[str]
    issue: Optional[str]
    number: Optional[str]
    pages: Optional[str]
    first_page: Optional[str]
    last_page: Optional[str]
    license: Optional[str]
    publisher: Optional[str]
    container_name: Optional[str]
    container_abbrev: Optional[str]
    container_issn: Optional[str]
    container_type: Optional[str]
    raw_references: Optional[List[str]]

    doi: Optional[str]
    pmid: Optional[str]
    pmcid: Optional[str]
    isbn13: Optional[str]
    publisher_ident: Optional[str]
    oai_id: Optional[str]

    abstract: Optional[str]
    pdf_fulltext_url: Optional[str]
    html_fulltext_url: Optional[str]
    xml_fulltext_url: Optional[str]


def html_extract_biblio(doc: HTMLParser) -> Optional[BiblioMetadata]:
    """
    TODO:
    - meta dc.identifier: parse DOI
    """

    meta: Any = dict()
    head = doc.css_first("head")
    if not head:
        return None

    for field, patterns in HEAD_META_PATTERNS.items():
        for pattern in patterns:
            val = head.css_first(pattern)
            #print((field, pattern, val))
            if val and val.attrs['content']:
                meta[field] = val.attrs['content']
                break

    for field, patterns in HEAD_META_LIST_PATTERNS.items():
        for pattern in patterns:
            val_list = head.css(pattern)
            if val_list:
                for val in val_list:
                    if val.attrs['content']:
                        if not field in meta:
                            meta[field] = []
                        meta[field].append(val.attrs['content'])
                break

    # TODO: replace with clean_doi() et al
    if meta.get('doi') and meta.get('doi').startswith('doi:'):
        meta['doi'] = meta['doi'][4:]

    raw_identifiers = meta.pop('raw_identifiers', [])
    for ident in raw_identifiers:
        if ident.startswith('doi:10.'):
            if not 'doi' in meta:
                meta['doi'] = ident.replace('doi:', '')
        elif ident.startswith('10.') and '/' in ident:
            if not 'doi' in meta:
                meta['doi'] = ident
        elif ident.startswith('isbn:'):
            if not 'isbn' in meta:
                meta['isbn'] = ident.replace('isbn:', '')

    raw_date = meta.pop('raw_date', None)
    if raw_date:
        parsed = dateparser.parse(raw_date)
        if parsed:
            meta['release_date'] = parsed.date()

    raw_release_type = meta.pop('raw_release_type', None)
    if raw_release_type:
        release_type = RELEASE_TYPE_MAP.get(raw_release_type.lower().strip())
        if release_type:
            meta['release_type'] = release_type

    return BiblioMetadata(**meta)
