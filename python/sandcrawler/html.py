import json
import re
import sys
import urllib.parse
from typing import Dict

from bs4 import BeautifulSoup

RESEARCHSQUARE_REGEX = re.compile(
    r'"url":"(https://assets.researchsquare.com/files/.{1,50}/v\d+/Manuscript.pdf)"'
)
IEEEXPLORE_REGEX = re.compile(r'"pdfPath":"(/.*?\.pdf)"')
OVID_JOURNAL_URL_REGEX = re.compile(r'journalURL = "(http.*)";')
SCIENCEDIRECT_BOUNCE_URL_REGEX = re.compile(r"window.location = '(http.*)';")


def extract_fulltext_url(html_url: str, html_body: bytes) -> Dict[str, str]:
    """
    Takes an HTML document (and URL), assumed to be a landing page, and tries
    to find a fulltext PDF url.

    On error, or if fails to extract a URL, returns an empty dict.
    """

    host_prefix = "/".join(html_url.split("/")[:3])
    try:
        soup = BeautifulSoup(html_body, "html.parser")
    except TypeError as te:
        print(f"{te} (url={html_url})", file=sys.stderr)
        return dict()
    except UnboundLocalError as ule:
        print(f"{ule} (url={html_url})", file=sys.stderr)
        return dict()

    ### General Tricks ###

    # highwire-style meta tag
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if not meta:
        meta = soup.find("meta", attrs={"name": "bepress_citation_pdf_url"})
    if not meta:
        meta = soup.find("meta", attrs={"name": "wkhealth_pdf_url"})
    if not meta:
        # researchgate does this; maybe others also?
        meta = soup.find("meta", attrs={"property": "citation_pdf_url"})
    if not meta:
        meta = soup.find("meta", attrs={"name": "eprints.document_url"})
    # if tag is only partially populated
    if meta and not meta.get("content"):
        meta = None
    # wiley has a weird almost-blank page we don't want to loop on
    if meta and "://onlinelibrary.wiley.com/doi/pdf/" not in html_url:
        url = meta["content"].strip()
        if "://doi.org/" in url:
            print(f"\tdoi.org in citation_pdf_url (loop?): {url}", file=sys.stderr)
        elif url.startswith("/"):
            if host_prefix + url == html_url:
                print("\tavoiding citation_pdf_url link-loop", file=sys.stderr)
            else:
                return dict(pdf_url=host_prefix + url, technique="citation_pdf_url")
        elif url.startswith("http"):
            if url == html_url:
                print("\tavoiding citation_pdf_url link-loop", file=sys.stderr)
            else:
                return dict(pdf_url=url, technique="citation_pdf_url")
        else:
            print("\tmalformed citation_pdf_url? {}".format(url), file=sys.stderr)

    meta = soup.find("meta", attrs={"name": "generator"})
    meta_generator = None
    if meta and meta.get("content"):
        meta_generator = meta["content"].strip()

    ### Publisher/Platform Specific ###

    # research square (researchsquare.com)
    if "researchsquare.com/article/" in html_url:
        # JSON in body with a field like:
        # "url":"https://assets.researchsquare.com/files/4a57970e-b002-4608-b507-b95967649483/v2/Manuscript.pdf"
        m = RESEARCHSQUARE_REGEX.search(html_body.decode("utf-8"))
        if m:
            url = m.group(1)
            assert len(url) < 4096
            return dict(release_stage="manuscript", pdf_url=url, technique="publisher")

    # elseiver linking hub
    # https://linkinghub.elsevier.com/retrieve/pii/S1569199319308975
    if "://linkinghub.elsevier.com/retrieve/pii/" in html_url:
        # <input type="hidden" name="redirectURL" value="http%3A%2F%2Fcysticfibrosisjournal.com%2Fretrieve%2Fpii%2FS1569199319308975" id="redirectURL"/>
        redirect = soup.find("input", attrs={"name": "redirectURL"})
        if redirect:
            url = redirect["value"].strip()
            if "http" in url:
                url = urllib.parse.unquote(url)
                # drop any the query parameter
                url = url.split("?via")[0]
                return dict(next_url=url, technique="elsevier-linkinghub")

    # sciencedirect PDF URL extract
    # https://www.sciencedirect.com/science/article/pii/S0169204621000670
    if "sciencedirect.com/science/article/pii/" in html_url and not html_url.endswith(".pdf"):
        json_tag = soup.find("script", attrs={"type": "application/json", "data-iso-key": "_0"})
        url = None
        if json_tag:
            try:
                json_text = json_tag.string
                json_meta = json.loads(json_text)
                pdf_meta = json_meta["article"]["pdfDownload"]["urlMetadata"]
                # https://www.sciencedirect.com/science/article/pii/S0169204621000670/pdfft?md5=c4a83d06b334b627ded74cf9423bfa56&pid=1-s2.0-S0169204621000670-main.pdf
                url = (
                    html_url
                    + pdf_meta["pdfExtension"]
                    + "?md5="
                    + pdf_meta["queryParams"]["md5"]
                    + "&pid="
                    + pdf_meta["queryParams"]["pid"]
                )
            except (KeyError, TypeError, json.JSONDecodeError):
                pass
        if url:
            return dict(pdf_url=url, technique="sciencedirect-munge-json")

    # sciencedirect PDF bounce page
    # https://www.sciencedirect.com/science/article/pii/S2590109519300424/pdfft?md5=854f43a44de186eb58674b8e20631691&pid=1-s2.0-S2590109519300424-main.pdf
    if "://www.sciencedirect.com/" in html_url and html_url.endswith(".pdf"):
        # window.location = 'https://pdf.sciencedirectassets.com/320270/AIP/1-s2.0-S2590109519300424/main.pdf?X-Amz-Security-Token=[...]&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20200110T210936Z&X-Amz-SignedHeaders=host&X-Amz-Expires=300&X-Amz-Credential=ASIAQ3PHCVTY23CMDBNC%2F20200110%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=[...]&hash=[...]&host=[...]&pii=S2590109519300424&tid=spdf-74468ebd-6be6-43ac-b294-ced86e8eea58&sid=[...]&type=client';
        m = SCIENCEDIRECT_BOUNCE_URL_REGEX.search(html_body.decode("utf-8"))
        if m:
            url = m.group(1)
            assert len(url) < 4000
            return dict(pdf_url=url, technique="sciencedirect-bounce")

    # ieeexplore.ieee.org
    # https://ieeexplore.ieee.org/document/8730316
    if "://ieeexplore.ieee.org/document/" in html_url:
        # JSON in body with a field like:
        # "pdfPath":"/iel7/6287639/8600701/08730316.pdf",
        m = IEEEXPLORE_REGEX.search(html_body.decode("utf-8"))
        if m:
            url = m.group(1)
            assert len(url) < 4096
            return dict(
                release_stage="published", pdf_url=host_prefix + url, technique="ieeexplore"
            )
    # https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=8730313
    if "://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber" in html_url:
        # HTML iframe like:
        # <iframe src="http://web.archive.org/web/20191026011528if_/https://ieeexplore.ieee.org/ielx7/6287639/8600701/08730313.pdf?tp=&amp;arnumber=8730313&amp;isnumber=8600701&amp;ref=" frameborder="0"></iframe>
        iframe = soup.find("iframe")
        if iframe and ".pdf" in iframe["src"]:
            return dict(pdf_url=iframe["src"], technique="iframe")

    # https://insights.ovid.com/crossref?an=00042307-202001000-00013
    # Ovid is some kind of landing page bounce portal tracking run-around.
    # Can extract actual journal URL from javascript blob in the HTML
    if "://insights.ovid.com/crossref" in html_url:
        # var journalURL = "https://journals.lww.com/co-urology/fulltext/10.1097/MOU.0000000000000689";
        m = OVID_JOURNAL_URL_REGEX.search(html_body.decode("utf-8"))
        if m:
            url = m.group(1)
            assert len(url) < 4096
            return dict(next_url=url, technique="ovid")

    # osf.io
    # https://osf.io/8phvx/
    # https://osf.io/preprints/socarxiv/8phvx/
    # wow, they ship total javascript crud! going to just guess download URL
    # based on URL for now. Maybe content type header would help?
    OSF_DOMAINS = [
        "://osf.io/",
        "://biohackrxiv.org/",
        "://psyarxiv.com/",
        "://arabixiv.org/",
        "://engrxiv.org/",
        "://edarxiv.org//",
        "://ecsarxiv.org/",
        "://ecoevorxiv.org/",
        "://frenxiv.org/",
        "://indiarxiv.org/",
        "://mindrxiv.org/",
        "://mediarxiv.org/",
        "://paleorxiv.org/",
        "://thesiscommons.org/",
    ]
    for domain in OSF_DOMAINS:
        if (
            domain in html_url
            and (len(html_url.split("/")) in [4, 5] or "/preprints/" in html_url)
            and "/download" not in html_url
        ):
            if not html_url.endswith("/"):
                next_url = html_url + "/download"
            else:
                next_url = html_url + "download"
            return dict(next_url=next_url, technique="osf-by-url")

    # wiley
    # https://onlinelibrary.wiley.com/doi/pdf/10.1111/1467-923X.12787
    if "://onlinelibrary.wiley.com/doi/pdf/" in html_url:
        if b"/doi/pdfdirect/" in html_body:
            next_url = html_url.replace("/doi/pdf/", "/doi/pdfdirect/")
            return dict(next_url=next_url, technique="wiley-pdfdirect")

    # arxiv abstract pages
    if "://arxiv.org/abs/" in html_url:
        url = html_url.replace("/abs/", "/pdf/")
        return dict(pdf_url=url, technique="arxiv-url")

    # american archivist (OA)
    # https://americanarchivist.org/doi/abs/10.17723/aarc.62.2.j475270470145630
    if "://americanarchivist.org/doi/" in html_url and "/doi/pdf" not in html_url:
        # use a more aggressive direct guess to avoid rate-limiting...
        if "/doi/10." in html_url:
            url = html_url.replace("/doi/10.", "/doi/pdf/10.")
            return dict(pdf_url=url, technique="archivist-url")
        # <a href="/doi/pdf/10.17723/aarc.62.2.j475270470145630" target="_blank">
        hrefs = soup.find_all("a", attrs={"target": "_blank"})
        for href in hrefs:
            url = href["href"].strip()
            if "/doi/pdf/" in url:
                if url.startswith("http"):
                    return dict(pdf_url=url, technique="publisher-href")
                elif url.startswith("/"):
                    return dict(pdf_url=host_prefix + url, technique="publisher-href")

    # protocols.io
    # https://www.protocols.io/view/flow-cytometry-protocol-mgdc3s6
    if "://www.protocols.io/view/" in html_url and not html_url.endswith(".pdf"):
        url = html_url + ".pdf"
        return dict(pdf_url=url, technique="protocolsio-url")

    # degruyter.com
    # https://www.degruyter.com/view/books/9783486594621/9783486594621-009/9783486594621-009.xml
    if "://www.degruyter.com/view/" in html_url and html_url.endswith(".xml"):
        url = html_url.replace("/view/", "/downloadpdf/").replace(".xml", ".pdf")
        return dict(pdf_url=url, technique="degruyter-url")

    # journals.lww.com (Wolters Kluwer)
    # https://journals.lww.com/spinejournal/Abstract/publishahead/Making_the_Most_of_Systematic_Reviews_and.94318.aspx
    # DISABLED: they seem to redirect our crawler back to a "Fulltext" page and
    # we never get the content.
    if "://journals.lww.com/" in html_url and False:
        # data-pdf-url="https://pdfs.journals.lww.com/spinejournal/9000/00000/Making_the_Most_of_Systematic_Reviews_and.94318.pdf?token=method|ExpireAbsolute;source|Journals;ttl|1582413672903;payload|mY8D3u1TCCsNvP5E421JYK6N6XICDamxByyYpaNzk7FKjTaa1Yz22MivkHZqjGP4kdS2v0J76WGAnHACH69s21Csk0OpQi3YbjEMdSoz2UhVybFqQxA7lKwSUlA502zQZr96TQRwhVlocEp/sJ586aVbcBFlltKNKo+tbuMfL73hiPqJliudqs17cHeLcLbV/CqjlP3IO0jGHlHQtJWcICDdAyGJMnpi6RlbEJaRheGeh5z5uvqz3FLHgPKVXJzdiVgCTnUeUQFYzcJRFhNtc2gv+ECZGji7HUicj1/6h85Y07DBRl1x2MGqlHWXUawD;hash|6cqYBa15ZK407m4VhFfJLw=="
        for line in html_body.split(b"\n"):
            if b"data-pdf-url=" in line:
                line = line.decode("utf-8")
                url = line.strip().replace("data-pdf-url=", "").replace('"', "")
                if url.startswith("http") and "pdfs.journals.lww.com" in url:
                    return dict(pdf_url=url, technique="journals.lww.com-jsvar")

    # www.ahajournals.org
    # https://www.ahajournals.org/doi/10.1161/circ.110.19.2977
    if "://www.ahajournals.org/doi/" in html_url and "/doi/pdf/" not in html_url:
        # <a href="/doi/pdf/10.1161/circ.110.19.2977?download=true">PDF download</a>
        if b"/doi/pdf/10." in html_body:
            url = html_url.replace("/doi/10.", "/doi/pdf/10.")
            url = url + "?download=true"
            return dict(pdf_url=url, technique="ahajournals-url")

    # ehp.niehs.nih.gov
    # https://ehp.niehs.nih.gov/doi/full/10.1289/EHP4709
    # https://ehp.niehs.nih.gov/doi/10.1289/ehp.113-a51
    if "://ehp.niehs.nih.gov/doi/" in html_url:
        # <a href="/doi/pdf/10.1289/EHP4709" target="_blank">
        if b"/doi/pdf/10." in html_body:
            url = html_url.replace("/doi/full/10.", "/doi/pdf/10.").replace(
                "/doi/10.", "/doi/pdf/10."
            )
            return dict(pdf_url=url, technique="ehp.niehs.nigh.gov-url")

    # cogentoa.com
    # https://www.cogentoa.com/article/10.1080/23311975.2017.1412873
    if "://www.cogentoa.com/article/" in html_url and ".pdf" not in html_url:
        # blech, it's a SPA! All JS
        # https://www.cogentoa.com/article/10.1080/23311975.2017.1412873.pdf
        url = html_url + ".pdf"
        return dict(pdf_url=url, technique="cogentoa-url")

    # chemrxiv.org (likely to be other figshare domains also)
    # https://chemrxiv.org/articles/Biradical_Formation_by_Deprotonation_in_Thiazole-Derivatives_The_Hidden_Nature_of_Dasatinib/10101419
    if "://chemrxiv.org/articles/" in html_url or ".figshare.org/articles/" in html_url:
        # <script id="app-data" type="text/json"> [...] </script>
        json_tag = soup.find("script", id="app-data", attrs={"type": "text/json"})
        if json_tag and json_tag.string:
            app_data = json.loads(json_tag.string)
            # "exportPdfDownloadUrl": "https://s3-eu-west-1.amazonaws.com/itempdf74155353254prod/10101419/Biradical_Formation_by_Deprotonation_in_Thiazole-Derivatives__The_Hidden_Nature_of_Dasatinib_v1.pdf"
            url = app_data.get("article", {}).get("exportPdfDownloadUrl")
            if url and url.startswith("http"):
                return dict(pdf_url=url, technique="figshare-json")

    # CNKI COVID-19 landing pages
    # http://en.gzbd.cnki.net/gzbt/detail/detail.aspx?FileName=HBGF202002003&DbName=GZBJ7920&DbCode=GZBJ
    if "://en.gzbd.cnki.net/KCMS/detail/detail.aspx" in html_url:
        # <a onclick="WriteKrsDownLog()" target="_blank" id="pdfDown" name="pdfDown" href="/gzbt/download.aspx?filename=4Q1ZYpFdKFUZ6FDR1QkRrolayRXV2ZzattyQ3QFa2JXTyZXUSV3QRFkbndzaGV2KyJXWZVEbFdVYnZndD9EOxg1Tj5Eeys2SMFzLZ5kcuFkM3dEbsR2ZjxEaShVdJhFdp90KhlVVzcjVVlXUVNHWBtWS5Rlb5cnc&amp;tablename=GZBJLAST2020&amp;dflag=pdfdown&#xA;                      "><i></i>PDF Download</a>
        href = soup.find("a", attrs={"id": "pdfDown"})
        if href:
            url = href["href"].strip().replace("&#xA;", "")
            if not url.startswith("http"):
                url = host_prefix + url
            return dict(pdf_url=url, technique="cnki-href")

    # RWTH AACHEN repository
    if "://publications.rwth-aachen.de/record/" in html_url:
        record_id = html_url.split("/")[-1]
        url = f"{html_url}/files/{record_id}.pdf"
        if record_id.isdigit() and url.encode("utf-8") in html_body:
            return dict(pdf_url=url, technique="rwth-aachen-url")

    # physchemaspects.ru
    if "://physchemaspects.ru/" in html_url and soup:
        for href in soup.find_all("a"):
            if href.text == "download PDF file":
                url = href["href"]
                if url.startswith("/"):
                    url = host_prefix + url
                return dict(pdf_url=url, technique="physchemaspects-href")

    # OJS 3 (some)
    if meta_generator and meta_generator.startswith("Open Journal Systems"):
        href = soup.find("a", attrs={"class": "obj_galley_link file"})
        if href and href.text and "pdf" in href.text.lower():
            url = href["href"].strip()
            if url.startswith("/"):
                url = host_prefix + url
            return dict(pdf_url=url, technique="ojs-galley-href")

    # ETH zurich e-periodica
    if "://www.e-periodica.ch/digbib/view" in html_url:
        url = html_url.replace("digbib/view", "cntmng").split("#")[0]
        if url.encode("utf-8") in html_body:
            return dict(pdf_url=url, technique="href-eperiodica")

    # JMIR
    # https://mhealth.jmir.org/2020/7/e17891/
    if ".jmir.org/" in html_url and "/pdf" not in html_url and html_url.endswith("/"):
        url = html_url + "pdf"
        return dict(pdf_url=url, technique="jmir-url")

    ### below here we are doing guesses

    # generic guess: try current URL plus .pdf, if it exists in the HTML body
    if ".pdf" not in html_url:
        url = html_url + ".pdf"
        if url.encode("utf-8") in html_body:
            return dict(pdf_url=url, technique="guess-url-plus-pdf")

    return dict()


def test_regex() -> None:
    lines = """
    blah
    var journalURL = "https://journals.lww.com/co-urology/fulltext/10.1097/MOU.0000000000000689";
    asdf"""
    m = OVID_JOURNAL_URL_REGEX.search(lines)
    assert m
    assert (
        m.group(1)
        == "https://journals.lww.com/co-urology/fulltext/10.1097/MOU.0000000000000689"
    )

    lines = """
            window.onload = function () {
                window.location = 'https://pdf.sciencedirectassets.com/320270/AIP/1-s2.0-S2590109519300424/main.pdf?X-Amz-Security-Token=IQoJb3JpZ2luX2VjEH0aCXVzLWVhc3QtMSJGMEQCICBF0dnrtKfpcs3T1kOjMS9w9gedqiLBrcbp4aKQSP8fAiAT9G426t6FWXHO2zPSXRFLq2eiqgbew2vkNKbcn87teyq9Awj1%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAIaDDA1OTAwMzU0Njg2NSIMnZcTRhbvMwF%2F5PA5KpEDdN%2FDI4V%2BNMDWQDFeAdUc99Lyxak%2B6vhAsfCBCf8hhvrRpalz75e74%2FXMAQwMN9m6i98o0Ljv9od7cuQEy8t%2B0DLzjzX5n3%2FxmpttowhMUm1jc8tBniLKBjwhTyiSHwhdeaVZf6x2zCJ0EIOWMNJHp3iFEqpaFvkRZbC1KWK4XPNNKo72HCvXuG7xmGrdHByz91AP7UgIYCy4hT10fnM43gbOE4wW8fqpgnvwCId%2F2u8k4rQoCLBqLYZzqshCRm1DBbsXCQhTwDXiMC2Ek3f63yKgw7rRCAxvs0vqirG%2B4mJ6LADaztAFMtKDPfnd4e%2B7%2FvnKU2NeotrqrkRgOkIAoFumbQXf20ky6mKWyHBk%2FxirVp60vUcLQpUm2Pcp6ythYxUi9IJxRGX8EF6aV4UHuCpUDUE7o8N84KUXIedUpytUZx7Xoxfk9w%2BR3%2FgX4LEHfkrWgiFAS3bVxNGOeV7GTwcXdcAggbdCaiAe46dfv7DDedx0KhVKOPH7obfvShqd6TYc0BjrV4sx61594ZJ3%2FO0ws7Lj8AU67AF17%2B1NZ3Ugu%2BwG9Ys9s7OxG8E4kBJ58vEY1yuBOQK9y2we4%2FTGPuqSxCuezqA%2BseslXYP%2FRc%2FZL9xx%2FUYaSjZhk1p1mhojxgBrckJYU7d8c4ELMPmtVy6R1yd2VDUoawEU8SB7nbNnMKzqQ3RgGgqGJiELys6dt%2FIr%2BVhpqM%2FZT4zadvzs8P%2FLoGzUHJKNZt0f99wLvZilphV92E%2BOUnwC4wbg3i3af3zozULwgEr7T%2FX2VsyREgexlzk76qMALPn0lgnciUyyQXxyUWAilXYQ0mQdXefh9lFfycczvt0UEuarX9p1sMwl8Ve5aw%3D%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20200110T210936Z&X-Amz-SignedHeaders=host&X-Amz-Expires=300&X-Amz-Credential=ASIAQ3PHCVTY23CMDBNC%2F20200110%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=b43525576e1a0fdbab581481a3fe6db2862cbb2c69f2860b70cc8d444ccd73d5&hash=ccd128dfe597e704224bdfb4b3358de29b2be5d95887c71076bdab1236ba9e42&host=68042c943591013ac2b2430a89b270f6af2c76d8dfd086a07176afe7c76c2c61&pii=S2590109519300424&tid=spdf-74468ebd-6be6-43ac-b294-ced86e8eea58&sid=f9676d658285a749c46b6d081d965bb12aa8gxrqa&type=client';
                refreshOriginalWindow();
            }
    """
    url = "https://pdf.sciencedirectassets.com/320270/AIP/1-s2.0-S2590109519300424/main.pdf?X-Amz-Security-Token=IQoJb3JpZ2luX2VjEH0aCXVzLWVhc3QtMSJGMEQCICBF0dnrtKfpcs3T1kOjMS9w9gedqiLBrcbp4aKQSP8fAiAT9G426t6FWXHO2zPSXRFLq2eiqgbew2vkNKbcn87teyq9Awj1%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAIaDDA1OTAwMzU0Njg2NSIMnZcTRhbvMwF%2F5PA5KpEDdN%2FDI4V%2BNMDWQDFeAdUc99Lyxak%2B6vhAsfCBCf8hhvrRpalz75e74%2FXMAQwMN9m6i98o0Ljv9od7cuQEy8t%2B0DLzjzX5n3%2FxmpttowhMUm1jc8tBniLKBjwhTyiSHwhdeaVZf6x2zCJ0EIOWMNJHp3iFEqpaFvkRZbC1KWK4XPNNKo72HCvXuG7xmGrdHByz91AP7UgIYCy4hT10fnM43gbOE4wW8fqpgnvwCId%2F2u8k4rQoCLBqLYZzqshCRm1DBbsXCQhTwDXiMC2Ek3f63yKgw7rRCAxvs0vqirG%2B4mJ6LADaztAFMtKDPfnd4e%2B7%2FvnKU2NeotrqrkRgOkIAoFumbQXf20ky6mKWyHBk%2FxirVp60vUcLQpUm2Pcp6ythYxUi9IJxRGX8EF6aV4UHuCpUDUE7o8N84KUXIedUpytUZx7Xoxfk9w%2BR3%2FgX4LEHfkrWgiFAS3bVxNGOeV7GTwcXdcAggbdCaiAe46dfv7DDedx0KhVKOPH7obfvShqd6TYc0BjrV4sx61594ZJ3%2FO0ws7Lj8AU67AF17%2B1NZ3Ugu%2BwG9Ys9s7OxG8E4kBJ58vEY1yuBOQK9y2we4%2FTGPuqSxCuezqA%2BseslXYP%2FRc%2FZL9xx%2FUYaSjZhk1p1mhojxgBrckJYU7d8c4ELMPmtVy6R1yd2VDUoawEU8SB7nbNnMKzqQ3RgGgqGJiELys6dt%2FIr%2BVhpqM%2FZT4zadvzs8P%2FLoGzUHJKNZt0f99wLvZilphV92E%2BOUnwC4wbg3i3af3zozULwgEr7T%2FX2VsyREgexlzk76qMALPn0lgnciUyyQXxyUWAilXYQ0mQdXefh9lFfycczvt0UEuarX9p1sMwl8Ve5aw%3D%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20200110T210936Z&X-Amz-SignedHeaders=host&X-Amz-Expires=300&X-Amz-Credential=ASIAQ3PHCVTY23CMDBNC%2F20200110%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=b43525576e1a0fdbab581481a3fe6db2862cbb2c69f2860b70cc8d444ccd73d5&hash=ccd128dfe597e704224bdfb4b3358de29b2be5d95887c71076bdab1236ba9e42&host=68042c943591013ac2b2430a89b270f6af2c76d8dfd086a07176afe7c76c2c61&pii=S2590109519300424&tid=spdf-74468ebd-6be6-43ac-b294-ced86e8eea58&sid=f9676d658285a749c46b6d081d965bb12aa8gxrqa&type=client"
    m = SCIENCEDIRECT_BOUNCE_URL_REGEX.search(lines)
    assert m
    assert m.group(1) == url
