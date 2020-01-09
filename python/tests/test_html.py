
import json
import pytest
import responses

from sandcrawler.html import extract_fulltext_url

def test_extract_fulltext_url():

    resp = extract_fulltext_url("asdf", "asdf")
    assert resp == {}

    resp = extract_fulltext_url(
        "http://dummy-site/",
        b"""<html>
        <head>
          <meta name="citation_pdf_url" content="http://www.example.com/content/271/20/11761.full.pdf">
        </head>
        <body>
        <h1>my big article here</h1>
        blah
        </body>
        </html>"""
    )
    assert resp['pdf_url'] == "http://www.example.com/content/271/20/11761.full.pdf"
    assert resp['technique'] == "citation_pdf_url"

    with open('tests/files/plos_one_article.html', 'r') as f:
        resp = extract_fulltext_url(
            "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0213978",
            f.read(),
        )
    assert resp['pdf_url'] == "https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0213978&type=printable"

    with open('tests/files/elife_article.html', 'r') as f:
        resp = extract_fulltext_url(
            "https://elifesciences.org/articles/44753",
            f.read(),
        )
    assert resp['pdf_url'] == "https://elifesciences.org/download/aHR0cHM6Ly9jZG4uZWxpZmVzY2llbmNlcy5vcmcvYXJ0aWNsZXMvNDQ3NTMvZWxpZmUtNDQ3NTMtdjIucGRm/elife-44753-v2.pdf?_hash=CfyqOqVryCR4OjcMTfcdpeIWAGZznmh9jXksYKYChCw%3D"

