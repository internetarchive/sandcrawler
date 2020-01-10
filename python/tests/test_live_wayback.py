
"""
This file contains tests to run against "live" wayback services. They default
to "skip" because you need authentication, and we shouldn't hit these services
automatically in CI.

Simply uncomment lines to run.
"""

import json
import pytest

from sandcrawler import CdxApiClient, CdxApiError, WaybackClient, WaybackError, PetaboxError


@pytest.fixture
def cdx_client():
    client = CdxApiClient()
    return client

@pytest.fixture
def wayback_client():
    client = WaybackClient()
    return client

@pytest.mark.skip(reason="hits prod services, requires auth")
def test_cdx_fetch(cdx_client):

    # org,plos,journals)/plosone/article?id=10.1371/journal.pone.0093949 20181105121428 https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0093949 text/html 200 OJ6FN5AAPU62VMMVJPXZYNBQD5VMYHFV - - 25338 240665973 MEDIACLOUD-20181105115107-crawl851/MEDIACLOUD-20181105115107-09234.warc.gz

    url = "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0093949"
    datetime = "20181105121428"
    resp = cdx_client.fetch(url, datetime)

    assert resp.url == url
    assert resp.datetime == datetime
    assert resp.sha1b32 == "OJ6FN5AAPU62VMMVJPXZYNBQD5VMYHFV"
    assert resp.warc_csize == 25338
    assert resp.warc_offset == 240665973
    assert resp.warc_path == "MEDIACLOUD-20181105115107-crawl851/MEDIACLOUD-20181105115107-09234.warc.gz"

    # bogus datetime; shouldn't match
    with pytest.raises(KeyError):
        resp = cdx_client.fetch(url, "12345678123456")

@pytest.mark.skip(reason="hits prod services, requires auth")
def test_cdx_lookup_best(cdx_client):

    url = "https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0093949&type=printable"
    resp = cdx_client.lookup_best(url, best_mimetype="application/pdf")

    # won't know datetime, hash, etc
    assert resp.url in (url, url.replace("https://", "http://"))
    assert resp.mimetype == "application/pdf"

@pytest.mark.skip(reason="hits prod services, requires auth")
def test_wayback_fetch(wayback_client):

    resp = wayback_client.fetch_petabox(25683, 2676464871, "archiveteam_archivebot_go_20171205210002/arstechnica.co.uk-inf-20171201-061309-bb65j-00021.warc.gz")

    assert resp.body

@pytest.mark.skip(reason="hits prod services, requires auth")
def test_lookup_resource_success(wayback_client):

    url = "https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0093949&type=printable"
    resp = wayback_client.lookup_resource(url)

    assert resp.hit == True
    assert resp.status == "success"
    assert resp.terminal_url in (url, url.replace("https://", "http://"))
    assert resp.cdx.url in (url, url.replace("https://", "http://"))

