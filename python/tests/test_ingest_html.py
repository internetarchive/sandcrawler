from sandcrawler.ingest_html import html_guess_platform

from selectolax.parser import HTMLParser

def test_html_guess_platform_no_icon_href() -> None:
    with open("tests/files/plos_one_article_no_icon_href.html", "r") as f:
        plos_html = f.read()
    parsed = HTMLParser(plos_html)
    result = html_guess_platform("", parsed)
    assert result == None
