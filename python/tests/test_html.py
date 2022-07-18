from sandcrawler.html import extract_fulltext_url


def test_extract_fulltext_url():

    resp = extract_fulltext_url("asdf", b"asdf")
    assert resp == {}
