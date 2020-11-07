
import datetime
import pytest

from sandcrawler.html_metadata import *


def test_html_metadata_plos() -> None:

    with open('tests/files/plos_one_article.html', 'r') as f:
        plos_html = f.read()

    meta = html_extract_biblio("http://example.org", HTMLParser(plos_html))
    assert meta is not None
    assert meta.title == "Assessment on reticuloendotheliosis virus infection in specific-pathogen-free chickens based on detection of yolk antibody"
    assert meta.doi == "10.1371/journal.pone.0213978"
    assert meta.pdf_fulltext_url == "https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0213978&type=printable"
    assert meta.contrib_names == [
        "Yang Li",
        "Tuanjie Wang",
        "Lin Wang",
        "Mingjun Sun",
        "Zhizhong Cui",
        "Shuang Chang",
        "Yongping Wu",
        "Xiaodong Zhang",
        "Xiaohui Yu",
        "Tao Sun",
        "Peng Zhao",
    ]
    assert meta.container_name == "PLOS ONE"
    assert meta.container_abbrev == "PLOS ONE"
    # "Apr 22, 2019"
    assert meta.release_date == datetime.date(year=2019, month=4, day=22)
    assert meta.first_page == "e0213978"
    assert meta.issue == "4"
    assert meta.volume == "14"
    assert meta.container_issn == "1932-6203"
    assert meta.publisher == "Public Library of Science"
    assert meta.raw_references and "citation_title=Reticuloendotheliosis virus sequences within the genomes of field strains of fowlpox virus display variability;citation_author=P Singh;citation_author=W. M. Schnitzlein;citation_author=D. N. Tripathy;citation_journal_title=J. Virol;citation_volume=77;citation_number=77;citation_first_page=5855;citation_last_page=5862;citation_publication_date=2003;" in meta.raw_references
    assert meta.release_type == "article-journal"


def test_html_metadata_elife() -> None:
    
    with open('tests/files/elife_article.html', 'r') as f:
        elife_html = f.read()

    meta = html_extract_biblio("http://example.org", HTMLParser(elife_html))
    assert meta is not None
    assert meta.title == "Parallel visual circuitry in a basal chordate"
    assert meta.doi == "10.7554/eLife.44753"
    assert meta.contrib_names == [
        "Matthew J Kourakis",
        "Cezar Borba",
        "Angela Zhang",
        "Erin Newman-Smith",
        "Priscilla Salas",
        "B Manjunath",
        "William C Smith",
    ]
    assert meta.container_name == "eLife"
    # 2019-04-18
    assert meta.release_date == datetime.date(year=2019, month=4, day=18)
    assert meta.publisher == "eLife Sciences Publications Limited"


def test_html_metadata_peerj() -> None:
 
    with open('tests/files/peerj_oa_article.html', 'r') as f:
        peerj_html = f.read()

    meta = html_extract_biblio("http://example.org", HTMLParser(peerj_html))
    assert meta is not None
    assert meta.title == "The state of OA: a large-scale analysis of the prevalence and impact of Open Access articles"
    assert meta.doi == "10.7717/peerj.4375"
    assert meta.contrib_names == [
            "Heather Piwowar",
      "Jason Priem",
      "Vincent Larivière",
      "Juan Pablo Alperin",
      "Lisa Matthias",
      "Bree Norlander",
      "Ashley Farley",
      "Jevin West",
      "Stefanie Haustein",
    ]
    assert meta.container_name == "PeerJ"
    # "2018-02-13"
    assert meta.release_date == datetime.date(year=2018, month=2, day=13)
    assert meta.xml_fulltext_url and ".xml" in meta.xml_fulltext_url


def test_html_metadata_nature() -> None:

    with open('tests/files/nature_article.html', 'r') as f:
        nature_html = f.read()

    meta = html_extract_biblio("http://example.org", HTMLParser(nature_html))
    assert meta is not None
    assert meta.title == "More than 100 scientific journals have disappeared from the Internet"
    assert meta.doi == "10.1038/d41586-020-02610-z"
    assert meta.contrib_names == [
        "Diana Kwon",
    ]
    assert meta.container_name == "Nature"
    # "2020-09-10"
    assert meta.release_date == datetime.date(year=2020, month=9, day=10)
    assert meta.publisher == "Nature Publishing Group"
    # note: some error in dublin code in nature HTML resulting in duplication
    assert meta.abstract == "Researchers have identified dozens of open-access journals that went offline between 2000 and 2019, and hundreds more that could be at risk.  Researchers have identified dozens of open-access journals that went offline between 2000 and 2019, and hundreds more that could be at risk."


def test_html_metadata_ojs3() -> None:

    with open('tests/files/first_monday_ojs3_landingpage.html', 'r') as f:
        ojs3_html = f.read()

    meta = html_extract_biblio("http://example.org", HTMLParser(ojs3_html))
    assert meta is not None
    assert meta.title == "Surveillance, stigma & sociotechnical design for HIV"
    assert meta.doi == "10.5210/fm.v25i10.10274"
    assert meta.contrib_names == [
        "Calvin Liang",
        "Jevan Alexander Hutson",
        "Os Keyes",
    ]
    assert meta.container_name == "First Monday"
    assert meta.container_abbrev == "1" # NOTE: bad source metadata
    assert meta.container_issn == "1396-0466"
    # "2020/09/10"
    assert meta.release_date == datetime.date(year=2020, month=9, day=10)
    assert meta.lang == "en"
    assert meta.abstract == "Online dating and hookup platforms have fundamentally changed people’s day-to-day practices of sex and love — but exist in tension with older social and medicolegal norms. This is particularly the case for people with HIV, who are frequently stigmatized, surveilled, ostracized, and incarcerated because of their status. Efforts to make intimate platforms “work” for HIV frequently focus on user-to-user interactions and disclosure of one’s HIV status but elide both the structural forces at work in regulating sex and the involvement of the state in queer lives. In an effort to foreground these forces and this involvement, we analyze the approaches that intimate platforms have taken in designing for HIV disclosure through a content analysis of 50 current platforms. We argue that the implicit reinforcement of stereotypes about who HIV is or is not a concern for, along with the failure to consider state practices when designing for data disclosure, opens up serious risks for HIV-positive and otherwise marginalized people. While we have no panacea for the tension between disclosure and risk, we point to bottom-up, communal, and queer approaches to design as a way of potentially making that tension easier to safely navigate."
    assert meta.html_fulltext_url == "https://firstmonday.org/ojs/index.php/fm/article/view/10274/9729"
    assert meta.release_type == "article-journal"


def test_html_metadata_dlib() -> None:

    with open('tests/files/dlib_05vanhyning.html', 'r') as f:
        dlib_html = f.read()

    meta = html_extract_biblio("http://example.org", HTMLParser(dlib_html))
    assert meta is not None
    assert meta.doi == "10.1045/may2017-vanhyning"
    # "2017-05-15"
    assert meta.release_date == datetime.date(year=2017, month=5, day=15)

def test_html_metadata_dc_case() -> None:
    """
    This tests that CSS selector <meta name=""> attribute lookups are not case-sensitive.
    """

    snippet = """
    <html>
    <head>
      <meta name="DC.Citation.Issue" content="123"/>
    </head>
    <body>Hi.</body>
    </html>"""

    meta = html_extract_biblio("http://example.org", HTMLParser(snippet))
    assert meta is not None
    assert meta.issue == "123"

@pytest.fixture
def adblock() -> Any:
    return load_adblock_rules()

def test_html_resources(adblock) -> None:

    with open('tests/files/dlib_05vanhyning.html', 'r') as f:
        dlib_html = f.read()

    resources = html_extract_resources(
        "http://www.dlib.org/dlib/may17/vanhyning/05vanhyning.html",
        HTMLParser(dlib_html),
        adblock,
    )

    assert dict(url="http://www.dlib.org/style/style1.css", type="stylesheet") in resources

    # check that adblock working
    for r in resources:
        assert '/ga.js' not in r['url']

    with open('tests/files/plos_one_article.html', 'r') as f:
        plos_html = f.read()

    resources = html_extract_resources(
        "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0213978",
        HTMLParser(plos_html),
        adblock,
    )

    # check that custom adblock working
    for r in resources:
        assert 'crossmark-cdn.crossref.org' not in r['url']

    with open('tests/files/first_monday_ojs3_landingpage.html', 'r') as f:
        monday_html = f.read()

    resources = html_extract_resources(
        "https://firstmonday.org/blah/",
        HTMLParser(monday_html),
        adblock,
    )

    with open('tests/files/elife_article.html', 'r') as f:
        elife_html = f.read()

    resources = html_extract_resources(
        "https://elife.org/blah/",
        HTMLParser(elife_html),
        adblock,
    )

    with open('tests/files/nature_article.html', 'r') as f:
        nature_html = f.read()

    resources = html_extract_resources(
        "https://nature.com/blah/",
        HTMLParser(nature_html),
        adblock,
    )

