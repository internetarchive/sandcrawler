
import datetime
import pytest

from sandcrawler.html_ingest import *


def test_html_extract_ojs3() -> None:

    with open('tests/files/first_monday_ojs3_fulltext.html', 'rb') as f:
        ojs3_html = f.read()

    fulltext = html_extract_fulltext_teixml(ojs3_html)
    assert fulltext['status'] == 'success'
