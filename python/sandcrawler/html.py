
import re
import sys
import urllib.parse

from bs4 import BeautifulSoup

RESEARCHSQUARE_REGEX = re.compile(r'"url":"(https://assets.researchsquare.com/files/.{1,50}/v\d+/Manuscript.pdf)"')

def extract_fulltext_url(html_url, html_body):
    """
    Takes an HTML document (and URL), assumed to be a landing page, and tries
    to find a fulltext PDF url.
    """

    host_prefix = '/'.join(html_url.split('/')[:3])
    soup = BeautifulSoup(html_body, 'html.parser')

    ### General Tricks ###

    # highwire-style meta tag
    meta = soup.find('meta', attrs={"name":"citation_pdf_url"})
    if not meta:
        meta = soup.find('meta', attrs={"name":"bepress_citation_pdf_url"})
    if meta:
        url = meta['content'].strip()
        if url.startswith('http'):
            return dict(pdf_url=url, technique='citation_pdf_url')
        else:
            sys.stderr.write("malformed citation_pdf_url? {}\n".format(url))

    # ACS (and probably others) like:
    #   https://pubs.acs.org/doi/10.1021/acs.estlett.9b00379
    #   <a href="/doi/pdf/10.1021/acs.estlett.9b00379" title="PDF" target="_blank" class="button_primary"><i class="icon-file-pdf-o"></i><span>PDF (1 MB)</span></a>
    href = soup.find('a', attrs={"title":"PDF"})
    if href:
        url = href['href'].strip()
        if url.startswith('http'):
            return dict(pdf_url=url, technique='href_title')
        elif url.startswith('/'):
            return dict(pdf_url=host_prefix+url, technique='href_title')

    ### Publisher/Platform Specific ###

    # eLife (elifesciences.org)
    if '://elifesciences.org/articles/' in html_url:
        anchor = soup.find("a", attrs={"data-download-type": "pdf-article"})
        if anchor:
            url = anchor['href'].strip()
            assert '.pdf' in url
            return dict(pdf_url=url)

    # research square (researchsquare.com)
    if 'researchsquare.com/article/' in html_url:
        # JSON in body with a field like:
        # "url":"https://assets.researchsquare.com/files/4a57970e-b002-4608-b507-b95967649483/v2/Manuscript.pdf"
        m = RESEARCHSQUARE_REGEX.search(html_body.decode('utf-8'))
        if m:
            url = m.group(1)
            assert len(url) < 1024
            return dict(release_stage="manuscript", pdf_url=url)

    # ehp.niehs.nih.gov
    # <a href="/doi/pdf/10.1289/EHP3950">
    if '://linkinghub.elsevier.com/retrieve/pii/' in html_url:
        redirect = soup.find("input", attrs={"name": "redirectURL"})
        if redirect:
            url = redirect['value'].strip()
            if 'sciencedirect.com' in url:
                url = urllib.parse.unquote(url)
                return dict(next_url=url)

    return dict()
