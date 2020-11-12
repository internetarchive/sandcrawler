
import sys
import datetime
from typing import List, Optional, Any, Tuple, Dict
import urllib.parse

import dateparser
from selectolax.parser import HTMLParser
import pydantic
import braveblock

from sandcrawler.misc import url_fuzzy_equal


# this is a map of metadata keys to CSS selectors
# sources for this list include:
#  - google scholar crawling notes (https://scholar.google.com/intl/ja/scholar/inclusion.html#indexing)
#  - inspection of actual publisher HTML
#  - http://div.div1.com.au/div-thoughts/div-commentaries/66-div-commentary-metadata
#  - "HTML meta tags used by journal articles"
#    https://gist.github.com/hubgit/5985963
# order of these are mostly by preference/quality (best option first), though
# also/sometimes re-ordered for lookup efficiency (lookup stops after first
# match)
HEAD_META_PATTERNS: Any = {
    "title": [
        "meta[name='citation_title']",
        "meta[name='eprints.title']",
        "meta[name='prism.title']",
        "meta[name='bepress_citation_title']",
        "meta[name='og:title']",
        "meta[name='dcterms.title']",
        "meta[name='dc.title']",
    ],
    "subtitle": [
        "meta[name='prism.subtitle']",
    ],
    "doi": [
        "meta[name='citation_doi']",
        "meta[name='DOI']",
        "meta[id='DOI']",
        "meta[name='prism.doi']",
        "meta[name='bepress_citation_doi']",
        "meta[name='dc.identifier.doi']",
        "meta[name='dc.identifier'][scheme='doi']",
    ],
    "pmid": [
        "meta[name='citation_pmid']",
    ],
    "abstract": [
        "meta[name='citation_abstract']",
        "meta[name='bepress_citation_abstract']",
        "meta[name='eprints.abstract']",
        "meta[name='dcterms.abstract']",
        "meta[name='prism.teaser']",
        "meta[name='dc.description']",
        "meta[name='og:description']",
    ],
    "container_name": [
        "meta[name='citation_journal_title']",
        "meta[name='bepress_citation_journal_title']",
        "meta[name='citation_conference_title']",
        "meta[name='bepress_citation_conference_title']",
        "meta[name='prism.publicationName']",
        "meta[name='eprints.publication']",
        "meta[name='dc.relation.ispartof']",
        "meta[name='dc.source']",
        "meta[property='og:site_name']",
    ],
    "container_abbrev": [
        "meta[name='citation_journal_abbrev']",
    ],
    "raw_date": [
        "meta[name='citation_publication_date']",
        "meta[name='bepress_citation_publication_date']",
        "meta[name='prism.publicationDate']",
        "meta[name='citation_date']",
        "meta[name='bepress_citation_date']",
        "meta[name='citation_online_date']",
        "meta[name='bepress_citation_online_date']",
        "meta[itemprop='datePublished']",
        "meta[name='article:published']",
        "meta[name='eprints.datestamp']",
        "meta[name='eprints.date']",
        "meta[name='dc.date.created']",
        "meta[name='dc.issued']",
        "meta[name='dcterms.date']",
        "meta[name='dc.date']",
    ],
    "release_year": [
        "meta[itemprop='citation_year']",
        "meta[itemprop='prism:copyrightYear']",
    ],
    "first_page": [
        "meta[name='citation_firstpage']",
        "meta[name='bepress_citation_firstpage']",
        "meta[name='prism.startingPage']",
        "meta[name='dc.citation.spage']",
    ],
    "last_page": [
        "meta[name='citation_lastpage']",
        "meta[name='bepress_citation_lastpage']",
        "meta[name='prism.endingPage']",
        "meta[name='dc.citation.epage']",
    ],
    "issue": [
        "meta[name='citation_issue']",
        "meta[name='bepress_citation_issue']",
        "meta[name='prism.issueIdentifier']",
        "meta[name='dc.citation.issue']",
    ],
    "volume": [
        "meta[name='citation_volume']",
        "meta[name='bepress_citation_volume']",
        "meta[name='prism.volume']",
        "meta[name='dc.citation.volume']",
    ],
    "number": [
        "meta[name='citation_technical_report_number']",
        "meta[name='bepress_citation_technical_report_number']",
        "meta[name='citation_number']",
        "meta[name='bepress_citation_number']",
        "meta[name='prism.number']",
    ],
    "container_issn": [
        "meta[name='citation_issn']",
        "meta[name='bepress_citation_issn']",
        "meta[name='prism.issn']",
        "meta[name='prism.eIssn']",
        "meta[name='eprints.issn']",
        "meta[name='dc.source.issn']",
    ],
    "isbn": [
        "meta[name='citation_isbn']",
        "meta[name='bepress_citation_isbn']",
        "meta[name='prism.isbn']",
    ],
    "publisher": [
        "meta[name='citation_publisher']",
        "meta[name='bepress_citation_publisher']",
        "meta[name='eprints.publisher']",
        "meta[name='citation_technical_report_institution']",
        "meta[name='dcterms.publisher']",
        "meta[name='dc.publisher']",
    ],
    "raw_release_type": [
        "meta[name='citation_article_type']",
        "meta[name='bepress_citation_article_type']",
        "meta[name='prism.contentType']",
        "meta[name='eprints.type']",
        "meta[name='dc.type']",
    ],
    "lang": [
        "meta[name='citation_language']",
        "meta[name='bepress_citation_language']",
        "meta[name='dcterms.language']",
        "meta[name='dc.language']",
        "meta[name='og:locale']",
    ],
}

HEAD_META_LIST_PATTERNS: Any = {
    "contrib_names": [
        "meta[name='citation_author']",
        "meta[name='bepress_citation_author']",
        "meta[name='eprints.creators_name']",
        "meta[name='dcterms.creator']",
        "meta[name='article:author']",
        "meta[name='dc.creator']",
        "meta[name='dc.contributor']",
    ],
    # TODO: citation_author_institution
    "raw_references": [
        "meta[name='citation_reference']",
    ],
    "raw_identifiers": [
        "meta[name='eprints.id_number']",
        "meta[name='dcterms.identifier']",
        "meta[name='dc.identifier']",
    ],
}

XML_FULLTEXT_PATTERNS: List[dict] = [
    {
        "selector": "meta[name='citation_xml_url']",
        "attr": "content",
        "technique": "citation_xml_url",
    },
    {
        "selector": "meta[name='fulltext_xml']",
        "attr": "content",
        "technique": "fulltext_xml",
    },
    {
        "selector": "link[rel='alternate'][type='application/xml']",
        "attr": "href",
        "technique": "alternate link",
    },
    {
        "selector": "link[rel='alternate'][type='text/xml']",
        "attr": "href",
        "technique": "alternate link",
    },
    {
        "in_doc_url": "scielo",
        "in_fulltext_url": "articleXML",
        "selector": "a[target='xml']",
        "attr": "href",
        "technique": "SciElo XML link",
    },
    {
        "in_doc_url": "/article/view/",
        "in_fulltext_url": "viewXML",
        "selector": "a[class='obj_galley_link']",
        "attr": "href",
        "technique": "OJS Gallery XML link",
    },
    {
        "in_fulltext_url": "/download/xml/",
        "selector": "a[title='XML']",
        "attr": "href",
        "technique": "ARPHA XML link",
        "example_page": "https://zookeys.pensoft.net/article/26391",
    },
]

HTML_FULLTEXT_PATTERNS: List[dict] = [
    {
        "selector": "meta[name='citation_fulltext_html_url']",
        "attr": "content",
        "technique": "citation_fulltext_html_url",
    },
    {
        "selector": "link[rel='alternate'][type='text/html']",
        "attr": "href",
        "technique": "alternate link",
    },
    {
        "in_doc_url": "/article/view/",
        "in_fulltext_url": "inline=1",
        "selector": "iframe[name='htmlFrame']",
        "attr": "src",
        "technique": "OJS HTML iframe",
    },
    {
        "in_doc_url": "dovepress.com",
        "in_fulltext_url": "-fulltext-",
        "selector": "a[id='view-full-text']",
        "attr": "href",
        "technique": "dovepress fulltext link",
    },
]

# This is a database of matching patterns. Most of these discovered by hand,
# looking at OA journal content that failed to craw/ingest.
PDF_FULLTEXT_PATTERNS: List[dict] = [
    {
        "selector": "head meta[name='citation_pdf_url']",
        "attr": "content",
        "technique": "citation_pdf_url",
    },
    {
        "selector": "head meta[name='bepress_citation_pdf_url']",
        "attr": "content",
        "technique": "citation_pdf_url",
    },
    {
        "in_doc_url": "journals.lww.com",
        "selector": "head meta[name='wkhealth_pdf_url']",
        "attr": "content",
        "technique": "wkhealth_pdf_url",
        "example_page": "https://journals.lww.com/otainternational/Fulltext/2019/03011/Trauma_systems_in_North_America.2.aspx",
    },
    {
        "selector": "head meta[propery='citation_pdf_url']",
        "attr": "content",
        "technique": "citation_pdf_url",
        # eg, researchgate
    },
    {
        "selector": "head meta[name='eprints.document_url']",
        "attr": "content",
        "technique": "citation_pdf_url (property)",
    },
    {
        "in_doc_url": "/doi/10.",
        "in_fulltext_url": "/doi/pdf/",
        "selector": "a.show-pdf",
        "attr": "href",
        "technique": "SAGE/UTP show-pdflink",
        "example_page": "https://journals.sagepub.com/doi/10.1177/2309499019888836",
        # also http://utpjournals.press/doi/10.3138/cjh.ach.54.1-2.05
    },
    {
        "in_doc_url": "/doi/10.",
        "in_fulltext_url": "/doi/pdf/",
        "selector": "a[title='PDF']",
        "attr": "href",
        "technique": "title=PDF link",
        "example_page": "https://pubs.acs.org/doi/10.1021/acs.estlett.9b00379",
    },
    {
        "in_doc_url": "/article/view/",
        "selector": "a#pdfDownloadLink",
        "attr": "href",
        "technique": "pdfDownloadLink link",
        "example_page": "http://www.revistas.unam.mx/index.php/rep/article/view/35503/32336",
    },
    {
        "in_fulltext_url": "/pdf/",
        "selector": "a.show-pdf",
        "attr": "href",
        "technique": "SAGE PDF link",
        "example_page": "http://journals.sagepub.com/doi/pdf/10.1177/2309499019888836",
    },
    {
        "in_doc_url": "://elifesciences.org/articles/",
        "in_fulltext_url": "/download/",
        "selector": "a[data-download-type='pdf-article']",
        "attr": "href",
        "technique": "eLife PDF link",
        "example_page": "https://elifesciences.org/articles/59841",
    },
    {
        "in_doc_url": "://www.jcancer.org/",
        "in_fulltext_url": ".pdf",
        "selector": ".divboxright a.text-button",
        "attr": "href",
        "technique": "jcancer PDF link",
        "example_page": "https://www.jcancer.org/v10p4038.htm",
    },
    {
        "in_doc_url": "://www.tandfonline.com/doi/full/10.",
        "in_fulltext_url": "/pdf/",
        "selector": "a.show-pdf",
        "attr": "href",
        "technique": "t+f show-pdf link",
        "example_page": "https://www.tandfonline.com/doi/full/10.1080/19491247.2019.1682234",
    },
    {
        "in_doc_url": "article_id=",
        "in_fulltext_url": "download.php",
        "selector": "a.file.pdf",
        "attr": "href",
        "technique": "pdf file link",
        "example_page": "http://journals.tsu.ru/psychology/&journal_page=archive&id=1815&article_id=40405",
    },
    {
        "in_doc_url": "/content/10.",
        "in_fulltext_url": "pdf",
        "selector": "a.pdf[title='Download']",
        "attr": "href",
        "technique": "pdf file link",
        "example_page": "https://www.eurosurveillance.org/content/10.2807/1560-7917.ES.2020.25.11.2000230",
    },
    {
        "selector": "embed[type='application/pdf']",
        "attr": "src",
        "technique": "PDF embed",
        "example_page": "http://www.jasstudies.com/DergiTamDetay.aspx?ID=3401",
    },
    {
        "in_doc_url": "/html/",
        "in_fulltext_url": "create_pdf",
        "selector": ".AbsPdfFigTab img[src='images/pdf-icon.jpg'] + a",
        "attr": "href",
        "technique": "PDF URL link",
        "example_page": "http://www.aed.org.cn/nyzyyhjxb/html/2018/4/20180408.htm",
    },
    {
        "in_doc_url": "/archive-detail/",
        "in_fulltext_url": ".pdf",
        "selector": ".contact-list a.download-pdf",
        "attr": "href",
        "technique": "PDF URL link",
        "example_page": "http://www.bezmialemscience.org/archives/archive-detail/article-preview/editorial/20439",
    },
]

FULLTEXT_URL_PATTERNS_SKIP = [
    # wiley has a weird almost-blank page we don't want to loop on
    "://onlinelibrary.wiley.com/doi/pdf/"
    "://doi.org/"
    "://dx.doi.org/"
]

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

    class Config:
        json_encoders = {
            datetime.date: lambda dt: dt.isoformat()
        }


def html_extract_fulltext_url(doc_url: str, doc: HTMLParser, patterns: List[dict]) -> Optional[Tuple[str, str]]:
    """
    Tries to quickly extract fulltext URLs using a set of patterns. This
    function is intendend to be generic across various extraction techniques.

    Returns null or a tuple of (url, technique)
    """
    self_doc_url: Optional[Tuple[str, str]] = None
    for pattern in patterns:
        if not 'selector' in pattern:
            continue
        if 'in_doc_url' in pattern:
            if not pattern['in_doc_url'] in doc_url:
                continue
        elem = doc.css_first(pattern['selector'])
        if not elem:
            continue
        if 'attr' in pattern:
            val = elem.attrs.get(pattern['attr'])
            if not val:
                continue
            val = urllib.parse.urljoin(doc_url, val)
            assert val
            if 'in_fulltext_url' in pattern:
                if not pattern['in_fulltext_url'] in val:
                    continue
            for skip_pattern in FULLTEXT_URL_PATTERNS_SKIP:
                if skip_pattern in val.lower():
                    continue
            if url_fuzzy_equal(doc_url, val):
                # don't link to self, unless no other options
                self_doc_url = (val, pattern.get('technique', 'unknown'))
                continue
            return (val, pattern.get('technique', 'unknown'))
    if self_doc_url:
        print(f"  WARN: returning fulltext URL pointing to self", file=sys.stderr)
        return self_doc_url
    return None

def html_extract_biblio(doc_url: str, doc: HTMLParser) -> Optional[BiblioMetadata]:

    meta: Any = dict()
    head = doc.css_first("head")
    if not head:
        return None

    for field, patterns in HEAD_META_PATTERNS.items():
        for pattern in patterns:
            val = head.css_first(pattern)
            #print((field, pattern, val))
            if val and val.attrs.get('content'):
                meta[field] = val.attrs['content']
                break

    for field, patterns in HEAD_META_LIST_PATTERNS.items():
        for pattern in patterns:
            val_list = head.css(pattern)
            if val_list:
                for val in val_list:
                    if val.attrs.get('content'):
                        if not field in meta:
                            meta[field] = []
                        meta[field].append(val.attrs['content'])
                break

    # (some) fulltext extractions
    pdf_fulltext_url = html_extract_fulltext_url(doc_url, doc, PDF_FULLTEXT_PATTERNS)
    if pdf_fulltext_url:
        meta['pdf_fulltext_url'] = pdf_fulltext_url[0]
    xml_fulltext_url = html_extract_fulltext_url(doc_url, doc, XML_FULLTEXT_PATTERNS)
    if xml_fulltext_url:
        meta['xml_fulltext_url'] = xml_fulltext_url[0]
    html_fulltext_url = html_extract_fulltext_url(doc_url, doc, HTML_FULLTEXT_PATTERNS)
    if html_fulltext_url:
        meta['html_fulltext_url'] = html_fulltext_url[0]

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

def load_adblock_rules() -> braveblock.Adblocker:
    """
    TODO: consider blocking very generic assets:
    - ://fonts.googleapis.com/css*
    - ://journals.plos.org/plosone/resource/img/icon.*
    """
    return braveblock.Adblocker(
        include_easylist=True,
        include_easyprivacy=True,
        rules=[
            "/favicon.ico^",
            "||fonts.googleapis.com^",
            "||widgets.figshare.com^",
            "||crossmark-cdn.crossref.org^",
            "||crossmark.crossref.org^",
            "||platform.twitter.com^",
            "||verify.nature.com^",
            "||s7.addthis.com^",
            "||www.mendeley.com^",
            "||pbs.twimg.com^",
            "||badge.dimensions.ai^",
            "||recaptcha.net^",

            # not sure about these CC badges (usually via a redirect)
            #"||licensebuttons.net^",
            #"||i.creativecommons.org^",

            # Should we skip jquery, or other generic javascript CDNs?
            #"||code.jquery.com^",
            #"||ajax.googleapis.com^",
            #"||cdnjs.cloudflare.com^",

            # badges, "share" buttons, tracking, etc
            "apis.google.com/js/plusone",
            "www.google.com/recaptcha/",
            "js/_getUACode.js"

            # PLOS images
            "/resource/img/icon.*.16.png^",
        ],
    )


def _extract_generic(doc: HTMLParser, selector: str, attrs: List[str], type_name: str) -> list:
    resources = []

    for node in doc.css(selector):
        for attr in attrs:
            url = node.attrs.get(attr)
            if url:
                resources.append(dict(url=url, type=type_name))

    return resources


def html_extract_resources(doc_url: str, doc: HTMLParser, adblock: braveblock.Adblocker) -> list:
    """
    This function tries to find all the important resources in a page. The
    presumption is that the HTML document is article fulltext, and we want the
    list of all resoures (by URL) necessary to replay the page.

    The returned resource URLs each have a type (script, img, css, etc), and
    should be fully-qualified URLs (not relative).

    Adblock filtering is run to remove unwanted resources.
    """
    resources = []

    # select various resource references
    resources += _extract_generic(doc, "script", ["src"], "script")
    resources += _extract_generic(doc, "link[rel='stylesheet']", ["href"], "stylesheet")
    # TODO: srcset and parse
    # eg: https://dfzljdn9uc3pi.cloudfront.net/2018/4375/1/fig-5-2x.jpg 1200w, https://dfzljdn9uc3pi.cloudfront.net/2018/4375/1/fig-5-1x.jpg 600w, https://dfzljdn9uc3pi.cloudfront.net/2018/4375/1/fig-5-small.jpg 355w
    resources += _extract_generic(doc, "img", ["src"], "image")
    resources += _extract_generic(doc, "audio", ["src"], "audio")
    resources += _extract_generic(doc, "video", ["src"], "media")
    resources += _extract_generic(doc, "source", ["src"], "media")
    resources += _extract_generic(doc, "track", ["src"], "media")
    resources += _extract_generic(doc, "iframe", ["src"], "subdocument")
    resources += _extract_generic(doc, "embed", ["src"], "media")

    # ensure URLs are absolute
    for r in resources:
        r['url'] = urllib.parse.urljoin(doc_url, r['url'])

    # filter using adblocker
    resources = [r for r in resources if adblock.check_network_urls(r['url'], source_url=doc_url, request_type=r['type']) == False]

    # remove duplicates
    resources = [dict(t) for t in {tuple(d.items()) for d in resources}]

    return resources

