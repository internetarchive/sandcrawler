
import re
import sys
import json
import urllib.parse

from bs4 import BeautifulSoup

RESEARCHSQUARE_REGEX = re.compile(r'"url":"(https://assets.researchsquare.com/files/.{1,50}/v\d+/Manuscript.pdf)"')
IEEEXPLORE_REGEX = re.compile(r'"pdfPath":"(/.*?\.pdf)"')
OVID_JOURNAL_URL_REGEX = re.compile(r'journalURL = "(http.*)";')
SCIENCEDIRECT_BOUNCE_URL_REGEX = re.compile(r"window.location = '(http.*)';")

def test_regex():
    lines = """
    blah
    var journalURL = "https://journals.lww.com/co-urology/fulltext/10.1097/MOU.0000000000000689";
    asdf"""
    m = OVID_JOURNAL_URL_REGEX.search(lines)
    assert m.group(1) == "https://journals.lww.com/co-urology/fulltext/10.1097/MOU.0000000000000689"

    lines = """
            window.onload = function () {
                window.location = 'https://pdf.sciencedirectassets.com/320270/AIP/1-s2.0-S2590109519300424/main.pdf?X-Amz-Security-Token=IQoJb3JpZ2luX2VjEH0aCXVzLWVhc3QtMSJGMEQCICBF0dnrtKfpcs3T1kOjMS9w9gedqiLBrcbp4aKQSP8fAiAT9G426t6FWXHO2zPSXRFLq2eiqgbew2vkNKbcn87teyq9Awj1%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAIaDDA1OTAwMzU0Njg2NSIMnZcTRhbvMwF%2F5PA5KpEDdN%2FDI4V%2BNMDWQDFeAdUc99Lyxak%2B6vhAsfCBCf8hhvrRpalz75e74%2FXMAQwMN9m6i98o0Ljv9od7cuQEy8t%2B0DLzjzX5n3%2FxmpttowhMUm1jc8tBniLKBjwhTyiSHwhdeaVZf6x2zCJ0EIOWMNJHp3iFEqpaFvkRZbC1KWK4XPNNKo72HCvXuG7xmGrdHByz91AP7UgIYCy4hT10fnM43gbOE4wW8fqpgnvwCId%2F2u8k4rQoCLBqLYZzqshCRm1DBbsXCQhTwDXiMC2Ek3f63yKgw7rRCAxvs0vqirG%2B4mJ6LADaztAFMtKDPfnd4e%2B7%2FvnKU2NeotrqrkRgOkIAoFumbQXf20ky6mKWyHBk%2FxirVp60vUcLQpUm2Pcp6ythYxUi9IJxRGX8EF6aV4UHuCpUDUE7o8N84KUXIedUpytUZx7Xoxfk9w%2BR3%2FgX4LEHfkrWgiFAS3bVxNGOeV7GTwcXdcAggbdCaiAe46dfv7DDedx0KhVKOPH7obfvShqd6TYc0BjrV4sx61594ZJ3%2FO0ws7Lj8AU67AF17%2B1NZ3Ugu%2BwG9Ys9s7OxG8E4kBJ58vEY1yuBOQK9y2we4%2FTGPuqSxCuezqA%2BseslXYP%2FRc%2FZL9xx%2FUYaSjZhk1p1mhojxgBrckJYU7d8c4ELMPmtVy6R1yd2VDUoawEU8SB7nbNnMKzqQ3RgGgqGJiELys6dt%2FIr%2BVhpqM%2FZT4zadvzs8P%2FLoGzUHJKNZt0f99wLvZilphV92E%2BOUnwC4wbg3i3af3zozULwgEr7T%2FX2VsyREgexlzk76qMALPn0lgnciUyyQXxyUWAilXYQ0mQdXefh9lFfycczvt0UEuarX9p1sMwl8Ve5aw%3D%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20200110T210936Z&X-Amz-SignedHeaders=host&X-Amz-Expires=300&X-Amz-Credential=ASIAQ3PHCVTY23CMDBNC%2F20200110%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=b43525576e1a0fdbab581481a3fe6db2862cbb2c69f2860b70cc8d444ccd73d5&hash=ccd128dfe597e704224bdfb4b3358de29b2be5d95887c71076bdab1236ba9e42&host=68042c943591013ac2b2430a89b270f6af2c76d8dfd086a07176afe7c76c2c61&pii=S2590109519300424&tid=spdf-74468ebd-6be6-43ac-b294-ced86e8eea58&sid=f9676d658285a749c46b6d081d965bb12aa8gxrqa&type=client';
                refreshOriginalWindow();
            }
    """
    url = "https://pdf.sciencedirectassets.com/320270/AIP/1-s2.0-S2590109519300424/main.pdf?X-Amz-Security-Token=IQoJb3JpZ2luX2VjEH0aCXVzLWVhc3QtMSJGMEQCICBF0dnrtKfpcs3T1kOjMS9w9gedqiLBrcbp4aKQSP8fAiAT9G426t6FWXHO2zPSXRFLq2eiqgbew2vkNKbcn87teyq9Awj1%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAIaDDA1OTAwMzU0Njg2NSIMnZcTRhbvMwF%2F5PA5KpEDdN%2FDI4V%2BNMDWQDFeAdUc99Lyxak%2B6vhAsfCBCf8hhvrRpalz75e74%2FXMAQwMN9m6i98o0Ljv9od7cuQEy8t%2B0DLzjzX5n3%2FxmpttowhMUm1jc8tBniLKBjwhTyiSHwhdeaVZf6x2zCJ0EIOWMNJHp3iFEqpaFvkRZbC1KWK4XPNNKo72HCvXuG7xmGrdHByz91AP7UgIYCy4hT10fnM43gbOE4wW8fqpgnvwCId%2F2u8k4rQoCLBqLYZzqshCRm1DBbsXCQhTwDXiMC2Ek3f63yKgw7rRCAxvs0vqirG%2B4mJ6LADaztAFMtKDPfnd4e%2B7%2FvnKU2NeotrqrkRgOkIAoFumbQXf20ky6mKWyHBk%2FxirVp60vUcLQpUm2Pcp6ythYxUi9IJxRGX8EF6aV4UHuCpUDUE7o8N84KUXIedUpytUZx7Xoxfk9w%2BR3%2FgX4LEHfkrWgiFAS3bVxNGOeV7GTwcXdcAggbdCaiAe46dfv7DDedx0KhVKOPH7obfvShqd6TYc0BjrV4sx61594ZJ3%2FO0ws7Lj8AU67AF17%2B1NZ3Ugu%2BwG9Ys9s7OxG8E4kBJ58vEY1yuBOQK9y2we4%2FTGPuqSxCuezqA%2BseslXYP%2FRc%2FZL9xx%2FUYaSjZhk1p1mhojxgBrckJYU7d8c4ELMPmtVy6R1yd2VDUoawEU8SB7nbNnMKzqQ3RgGgqGJiELys6dt%2FIr%2BVhpqM%2FZT4zadvzs8P%2FLoGzUHJKNZt0f99wLvZilphV92E%2BOUnwC4wbg3i3af3zozULwgEr7T%2FX2VsyREgexlzk76qMALPn0lgnciUyyQXxyUWAilXYQ0mQdXefh9lFfycczvt0UEuarX9p1sMwl8Ve5aw%3D%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20200110T210936Z&X-Amz-SignedHeaders=host&X-Amz-Expires=300&X-Amz-Credential=ASIAQ3PHCVTY23CMDBNC%2F20200110%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=b43525576e1a0fdbab581481a3fe6db2862cbb2c69f2860b70cc8d444ccd73d5&hash=ccd128dfe597e704224bdfb4b3358de29b2be5d95887c71076bdab1236ba9e42&host=68042c943591013ac2b2430a89b270f6af2c76d8dfd086a07176afe7c76c2c61&pii=S2590109519300424&tid=spdf-74468ebd-6be6-43ac-b294-ced86e8eea58&sid=f9676d658285a749c46b6d081d965bb12aa8gxrqa&type=client"
    m = SCIENCEDIRECT_BOUNCE_URL_REGEX.search(lines)
    assert m.group(1) == url


def extract_fulltext_url(html_url, html_body):
    """
    Takes an HTML document (and URL), assumed to be a landing page, and tries
    to find a fulltext PDF url.

    On error, or if fails to extract a URL, returns an empty dict.
    """

    host_prefix = '/'.join(html_url.split('/')[:3])
    try:
        soup = BeautifulSoup(html_body, 'html.parser')
    except TypeError as te:
        print("{} (url={})".format(te, html_url, file=sys.stderr))
        return dict()

    ### General Tricks ###

    # highwire-style meta tag
    meta = soup.find('meta', attrs={"name":"citation_pdf_url"})
    if not meta:
        meta = soup.find('meta', attrs={"name":"bepress_citation_pdf_url"})
    if not meta:
        # researchgate does this; maybe others also?
        meta = soup.find('meta', attrs={"property":"citation_pdf_url"})
    # wiley has a weird almost-blank page we don't want to loop on
    if meta and not "://onlinelibrary.wiley.com/doi/pdf/" in html_url:
        url = meta['content'].strip()
        if url.startswith('/'):
            return dict(pdf_url=host_prefix+url, technique='citation_pdf_url')
        elif url.startswith('http'):
            return dict(pdf_url=url, technique='citation_pdf_url')
        else:
            print("malformed citation_pdf_url? {}".format(url), file=sys.stderr)

    # sage, and also utpjournals (see below)
    # https://journals.sagepub.com/doi/10.1177/2309499019888836
    # <a href="http://journals.sagepub.com/doi/pdf/10.1177/2309499019888836" class="show-pdf" target="_self">
    # <a href="http://utpjournals.press/doi/pdf/10.3138/cjh.ach.54.1-2.05" class="show-pdf" target="_blank">
    href = soup.find('a', attrs={"class":"show-pdf"})
    if href:
        url = href['href'].strip()
        if url.startswith('http'):
            return dict(pdf_url=url, technique='href_show-pdf')

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

    # http://www.jasstudies.com/DergiTamDetay.aspx?ID=3401
    # <embed src="/files/jass_makaleler/1359848334_33-Okt.%20Yasemin%20KARADEM%C4%B0R.pdf" type="application/pdf" />
    embed = soup.find('embed', attrs={"type": "application/pdf"})
    if embed:
        url = embed['src'].strip()
        if url.startswith('/'):
            url = host_prefix+url
        if url.startswith('http'):
            return dict(pdf_url=url, technique='embed_type')

    ### Publisher/Platform Specific ###

    # eLife (elifesciences.org)
    if '://elifesciences.org/articles/' in html_url:
        anchor = soup.find("a", attrs={"data-download-type": "pdf-article"})
        if anchor:
            url = anchor['href'].strip()
            assert '.pdf' in url
            return dict(pdf_url=url, technique='publisher')

    # research square (researchsquare.com)
    if 'researchsquare.com/article/' in html_url:
        # JSON in body with a field like:
        # "url":"https://assets.researchsquare.com/files/4a57970e-b002-4608-b507-b95967649483/v2/Manuscript.pdf"
        m = RESEARCHSQUARE_REGEX.search(html_body.decode('utf-8'))
        if m:
            url = m.group(1)
            assert len(url) < 4096
            return dict(release_stage="manuscript", pdf_url=url, technique='publisher')

    # elseiver linking hub
    # https://linkinghub.elsevier.com/retrieve/pii/S1569199319308975
    if '://linkinghub.elsevier.com/retrieve/pii/' in html_url:
        # <input type="hidden" name="redirectURL" value="http%3A%2F%2Fcysticfibrosisjournal.com%2Fretrieve%2Fpii%2FS1569199319308975" id="redirectURL"/>
        redirect = soup.find("input", attrs={"name": "redirectURL"})
        if redirect:
            url = redirect['value'].strip()
            if 'http' in url:
                url = urllib.parse.unquote(url)
                # drop any the query parameter
                url = url.split('?via')[0]
                return dict(next_url=url, technique="elsevier-linkinghub")

    # sciencedirect PDF bounce page
    # https://www.sciencedirect.com/science/article/pii/S2590109519300424/pdfft?md5=854f43a44de186eb58674b8e20631691&pid=1-s2.0-S2590109519300424-main.pdf
    if '://www.sciencedirect.com/' in html_url and html_url.endswith(".pdf"):
        # window.location = 'https://pdf.sciencedirectassets.com/320270/AIP/1-s2.0-S2590109519300424/main.pdf?X-Amz-Security-Token=[...]&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20200110T210936Z&X-Amz-SignedHeaders=host&X-Amz-Expires=300&X-Amz-Credential=ASIAQ3PHCVTY23CMDBNC%2F20200110%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=[...]&hash=[...]&host=[...]&pii=S2590109519300424&tid=spdf-74468ebd-6be6-43ac-b294-ced86e8eea58&sid=[...]&type=client';
        m = SCIENCEDIRECT_BOUNCE_URL_REGEX.search(html_body.decode('utf-8'))
        if m:
            url = m.group(1)
            assert len(url) < 4000
            return dict(pdf_url=url, technique="sciencedirect-bounce")

    # ieeexplore.ieee.org
    # https://ieeexplore.ieee.org/document/8730316
    if '://ieeexplore.ieee.org/document/' in html_url:
        # JSON in body with a field like:
        # "pdfPath":"/iel7/6287639/8600701/08730316.pdf",
        m = IEEEXPLORE_REGEX.search(html_body.decode('utf-8'))
        if m:
            url = m.group(1)
            assert len(url) < 4096
            return dict(release_stage="published", pdf_url=host_prefix+url, technique="ieeexplore")
    # https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=8730313
    if '://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber' in html_url:
        # HTML iframe like:
        # <iframe src="http://web.archive.org/web/20191026011528if_/https://ieeexplore.ieee.org/ielx7/6287639/8600701/08730313.pdf?tp=&amp;arnumber=8730313&amp;isnumber=8600701&amp;ref=" frameborder="0"></iframe>
        iframe = soup.find("iframe")
        if iframe and '.pdf' in iframe['src']:
            return dict(pdf_url=iframe['src'], technique="iframe")

    # utpjournals.press
    # https://utpjournals.press/doi/10.3138/cjh.ach.54.1-2.05
    if '://utpjournals.press/doi/10.' in html_url:
        # <a href="http://utpjournals.press/doi/pdf/10.3138/cjh.ach.54.1-2.05" class="show-pdf" target="_blank">
        href = soup.find('a', attrs={"class":"show-pdf"})
        if href:
            url = href['href'].strip()
            if url.startswith('http'):
                return dict(pdf_url=url, technique='publisher-href')

    # https://www.jcancer.org/v10p4038.htm
    # simple journal-specific href
    if '://www.jcancer.org/' in html_url and html_url.endswith(".htm"):
        # <a href='v10p4038.pdf' class='textbutton'>PDF</a>
        href = soup.find('a', attrs={"class":"textbutton"})
        if href:
            url = href['href'].strip()
            if url.endswith(".pdf") and not "http" in url:
                return dict(pdf_url=host_prefix+"/"+url, technique='journal-href')

    # https://insights.ovid.com/crossref?an=00042307-202001000-00013
    # Ovid is some kind of landing page bounce portal tracking run-around.
    # Can extract actual journal URL from javascript blob in the HTML
    if '://insights.ovid.com/crossref' in html_url:
        # var journalURL = "https://journals.lww.com/co-urology/fulltext/10.1097/MOU.0000000000000689";
        m = OVID_JOURNAL_URL_REGEX.search(html_body.decode('utf-8'))
        if m:
            url = m.group(1)
            assert len(url) < 4096
            return dict(next_url=url, technique='ovid')

    # osf.io
    # https://osf.io/8phvx/
    # https://osf.io/preprints/socarxiv/8phvx/
    # wow, they ship total javascript crud! going to just guess download URL
    # based on URL for now. Maybe content type header would help?
    if '://osf.io/' in html_url and not '/download' in html_url:
        if not html_url.endswith("/"):
            next_url = html_url+"/download"
        else:
            next_url = html_url+"download"
        return dict(next_url=next_url, technique='osf-by-url')

    # wiley
    # https://onlinelibrary.wiley.com/doi/pdf/10.1111/1467-923X.12787
    if "://onlinelibrary.wiley.com/doi/pdf/" in html_url:
        if b"/doi/pdfdirect/" in html_body:
            next_url = html_url.replace('/doi/pdf/', '/doi/pdfdirect/')
            return dict(next_url=next_url, technique='wiley-pdfdirect')

    # taylor and frances
    # https://www.tandfonline.com/doi/full/10.1080/19491247.2019.1682234
    # <a href="/doi/pdf/10.1080/19491247.2019.1682234?needAccess=true" class="show-pdf" target="_blank">
    if "://www.tandfonline.com/doi/full/10." in html_url:
        href = soup.find('a', attrs={"class":"show-pdf"})
        if href:
            url = href['href'].strip()
            if "/pdf/" in url:
                return dict(pdf_url=host_prefix+url, technique='publisher-href')

    # arxiv abstract pages
    if "://arxiv.org/abs/" in html_url:
        url = html_url.replace("/abs/", "/pdf/")
        return dict(pdf_url=url, technique='arxiv-url')

    # american archivist (OA)
    # https://americanarchivist.org/doi/abs/10.17723/aarc.62.2.j475270470145630
    if "://americanarchivist.org/doi/" in html_url and not "/doi/pdf" in html_url:
        # <a href="/doi/pdf/10.17723/aarc.62.2.j475270470145630" target="_blank">
        hrefs = soup.find_all('a', attrs={"target":"_blank"})
        for href in hrefs:
            url = href['href'].strip()
            if "/doi/pdf/" in url:
                if url.startswith('http'):
                    return dict(pdf_url=url, technique='publisher-href')
                elif url.startswith('/'):
                    return dict(pdf_url=host_prefix+url, technique='publisher-href')

    # protocols.io
    # https://www.protocols.io/view/flow-cytometry-protocol-mgdc3s6
    if "://www.protocols.io/view/" in html_url and not html_url.endswith(".pdf"):
        url = html_url + ".pdf"
        return dict(pdf_url=url, technique='protocolsio-url')

    # degruyter.com
    # https://www.degruyter.com/view/books/9783486594621/9783486594621-009/9783486594621-009.xml
    if "://www.degruyter.com/view/" in html_url and html_url.endswith(".xml"):
        url = html_url.replace('/view/', '/downloadpdf/').replace('.xml', '.pdf')
        return dict(pdf_url=url, technique='degruyter-url')

    # journals.lww.com (Wolters Kluwer)
    # https://journals.lww.com/spinejournal/Abstract/publishahead/Making_the_Most_of_Systematic_Reviews_and.94318.aspx
    # DISABLED: they seem to redirect our crawler back to a "Fulltext" page and
    # we never get the content.
    if "://journals.lww.com/" in html_url and False:
        # data-pdf-url="https://pdfs.journals.lww.com/spinejournal/9000/00000/Making_the_Most_of_Systematic_Reviews_and.94318.pdf?token=method|ExpireAbsolute;source|Journals;ttl|1582413672903;payload|mY8D3u1TCCsNvP5E421JYK6N6XICDamxByyYpaNzk7FKjTaa1Yz22MivkHZqjGP4kdS2v0J76WGAnHACH69s21Csk0OpQi3YbjEMdSoz2UhVybFqQxA7lKwSUlA502zQZr96TQRwhVlocEp/sJ586aVbcBFlltKNKo+tbuMfL73hiPqJliudqs17cHeLcLbV/CqjlP3IO0jGHlHQtJWcICDdAyGJMnpi6RlbEJaRheGeh5z5uvqz3FLHgPKVXJzdiVgCTnUeUQFYzcJRFhNtc2gv+ECZGji7HUicj1/6h85Y07DBRl1x2MGqlHWXUawD;hash|6cqYBa15ZK407m4VhFfJLw=="
        for line in html_body.split(b'\n'):
            if b"data-pdf-url=" in line:
                line = line.decode('utf-8')
                url = line.strip().replace('data-pdf-url=', '').replace('"', '')
                if url.startswith('http') and 'pdfs.journals.lww.com' in url:
                    return dict(pdf_url=url, technique='journals.lww.com-jsvar')

    # www.ahajournals.org
    # https://www.ahajournals.org/doi/10.1161/circ.110.19.2977
    if "://www.ahajournals.org/doi/" in html_url and not '/doi/pdf/' in html_url:
        # <a href="/doi/pdf/10.1161/circ.110.19.2977?download=true">PDF download</a>
        if b'/doi/pdf/10.' in html_body:
            url = html_url.replace('/doi/10.', '/doi/pdf/10.')
            url = url + "?download=true"
            return dict(pdf_url=url, technique='ahajournals-url')

    # ehp.niehs.nih.gov
    # https://ehp.niehs.nih.gov/doi/full/10.1289/EHP4709
    if "://ehp.niehs.nih.gov/doi/full/" in html_url:
        # <a href="/doi/pdf/10.1289/EHP4709" target="_blank">
        if b'/doi/pdf/10.' in html_body:
            url = html_url.replace('/doi/full/10.', '/doi/pdf/10.')
            return dict(pdf_url=url, technique='ehp.niehs.nigh.gov-url')

    # journals.tsu.ru (and maybe others)
    # http://journals.tsu.ru/psychology/&journal_page=archive&id=1815&article_id=40405
    # <a class='file pdf' href='http://journals.tsu.ru/engine/download.php?id=150921&area=files'>Скачать электронную версию публикации</a>
    href = soup.find('a', attrs={"class":"file pdf"})
    if href:
        url = href['href'].strip()
        if url.startswith('http'):
            return dict(pdf_url=url, technique='href_file_pdf-pdf')

    # cogentoa.com
    # https://www.cogentoa.com/article/10.1080/23311975.2017.1412873
    if "://www.cogentoa.com/article/" in html_url and not ".pdf" in html_url:
        # blech, it's a SPA! All JS
        # https://www.cogentoa.com/article/10.1080/23311975.2017.1412873.pdf
        url = html_url + ".pdf"
        return dict(pdf_url=url, technique='cogentoa-url')

    # chemrxiv.org (likely to be other figshare domains also)
    # https://chemrxiv.org/articles/Biradical_Formation_by_Deprotonation_in_Thiazole-Derivatives_The_Hidden_Nature_of_Dasatinib/10101419
    if "://chemrxiv.org/articles/" in html_url or '.figshare.org/articles/' in html_url:
        # <script id="app-data" type="text/json"> [...] </script>
        json_tag = soup.find('script', id="app-data", attrs={"type": "text/json"})
        if json_tag.string:
            app_data = json.loads(json_tag.string)
            # "exportPdfDownloadUrl": "https://s3-eu-west-1.amazonaws.com/itempdf74155353254prod/10101419/Biradical_Formation_by_Deprotonation_in_Thiazole-Derivatives__The_Hidden_Nature_of_Dasatinib_v1.pdf"
            url = app_data.get('article', {}).get('exportPdfDownloadUrl')
            if url and url.startswith('http'):
                return dict(pdf_url=url, technique='figshare-json')

    return dict()
