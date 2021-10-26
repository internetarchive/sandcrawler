"""
This file contains tests to run against "live" wayback services. They default
to "skip" because you need authentication, and we shouldn't hit these services
automatically in CI.

Simply uncomment lines to run.
"""

import json

import pytest

from sandcrawler import (CdxApiClient, CdxApiError, CdxPartial, PetaboxError, SavePageNowClient,
                         SavePageNowError, WaybackClient, WaybackError, gen_file_metadata)


@pytest.fixture
def cdx_client():
    client = CdxApiClient()
    return client


@pytest.fixture
def wayback_client():
    client = WaybackClient()
    return client


@pytest.fixture
def spn_client():
    client = SavePageNowClient()
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
    assert resp.status_code == 200

    url = "https://americanarchivist.org/doi/abs/10.17723/aarc.62.2.gu33570g87v71007"
    resp = cdx_client.lookup_best(url, best_mimetype="application/pdf")

    assert resp.url in (url, url.replace("https://", "http://"))
    assert resp.mimetype == "text/html"
    assert resp.status_code == 200


@pytest.mark.skip(reason="hits prod services, requires auth")
def test_wayback_fetch(wayback_client):

    resp = wayback_client.fetch_petabox(
        25683, 2676464871,
        "archiveteam_archivebot_go_20171205210002/arstechnica.co.uk-inf-20171201-061309-bb65j-00021.warc.gz"
    )

    assert resp.body


@pytest.mark.skip(reason="hits prod services, requires auth")
def test_lookup_resource_success(wayback_client):

    url = "https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0093949&type=printable"
    resp = wayback_client.lookup_resource(url)

    assert resp.hit == True
    assert resp.status == "success"
    assert resp.terminal_url in (url, url.replace("https://", "http://"))
    assert resp.cdx.url in (url, url.replace("https://", "http://"))


@pytest.mark.skip(reason="hits prod services, requires auth")
def test_cdx_fetch_spn2(cdx_client):

    # https://linkinghub.elsevier.com/retrieve/pii/S2590109519300424 20200110210133

    # com,elsevier,linkinghub)/retrieve/pii/s2590109519300424 20191201203206 https://linkinghub.elsevier.com/retrieve/pii/S2590109519300424 text/html 200 FPXVUJR7RXVGO6RIY5HYB6JVT7OD53SG - - 5026 364192270 liveweb-20191201204645/live-20191201195942-wwwb-app52.us.archive.org.warc.gz
    # com,elsevier,linkinghub)/retrieve/pii/s2590109519300424 20200110210044 https://linkinghub.elsevier.com/retrieve/pii/S2590109519300424 text/html 200 OIQ3TKPBQLYYXQDIG7D2ZOK7IJEUEAQ7 - - 5130 710652442 liveweb-20200110204521-wwwb-spn20.us.archive.org-8001.warc.gz
    # com,elsevier,linkinghub)/retrieve/pii/s2590109519300424 20200110210133 https://linkinghub.elsevier.com/retrieve/pii/S2590109519300424 text/html 200 G2MSFAYELECMFGKTYEHUN66WWNW4HXKQ - - 5126 544508422 liveweb-20200110205247-wwwb-spn01.us.archive.org-8000.warc.gz

    url = "https://linkinghub.elsevier.com/retrieve/pii/S2590109519300424"
    datetime = "20200110210133"
    resp = cdx_client.fetch(url, datetime, filter_status_code=200)

    assert resp.url == url
    assert resp.datetime == datetime
    assert resp.sha1b32 == "G2MSFAYELECMFGKTYEHUN66WWNW4HXKQ"
    assert resp.status_code == 200

    # https://onlinelibrary.wiley.com/doi/pdf/10.1002/lrh2.10209 20200110222410

    #com,wiley,onlinelibrary)/doi/pdf/10.1002/lrh2.10209 20200110222410 https://onlinelibrary.wiley.com/doi/pdf/10.1002/lrh2.10209 text/html 200 VYW7JXFK6EC2KC537N5B7PHYZC4B6MZL - - 9006 815069841 liveweb-20200110214015-wwwb-spn18.us.archive.org-8002.warc.gz
    #com,wiley,onlinelibrary)/doi/pdf/10.1002/lrh2.10209 20200110222410 https://onlinelibrary.wiley.com/doi/pdf/10.1002/lrh2.10209 text/html 302 AFI55BZE23HDTTEERUFKRP6WQVO3LOLS - - 1096 815066572 liveweb-20200110214015-wwwb-spn18.us.archive.org-8002.warc.gz
    #com,wiley,onlinelibrary)/doi/pdf/10.1002/lrh2.10209 20200110222422 https://onlinelibrary.wiley.com/doi/pdf/10.1002/lrh2.10209 text/html 302 AFI55BZE23HDTTEERUFKRP6WQVO3LOLS - - 1094 307563475 liveweb-20200110214449-wwwb-spn18.us.archive.org-8003.warc.gz

    url = "https://onlinelibrary.wiley.com/doi/pdf/10.1002/lrh2.10209"
    datetime = "20200110222410"
    resp = cdx_client.fetch(url, datetime, filter_status_code=200)

    assert resp.url == url
    assert resp.datetime == datetime
    assert resp.sha1b32 == "VYW7JXFK6EC2KC537N5B7PHYZC4B6MZL"
    assert resp.status_code == 200


@pytest.mark.skip(reason="hits prod services, requires auth")
def test_lookup_ftp(wayback_client):
    # ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/80/23/10.1177_1559827617708562.PMC6236633.pdf
    # ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/ad/ab/mmr-17-05-6969.PMC5928650.pdf
    # ftp://ftp.cs.utexas.edu/pub/qsim/papers/Xu-crv-08.pdf

    # revisit!
    url = "ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/ad/ab/mmr-17-05-6969.PMC5928650.pdf"
    resp = wayback_client.lookup_resource(url)

    assert resp.hit == True
    assert resp.status == "success"
    assert resp.terminal_url == url
    assert resp.terminal_status_code == 226
    assert resp.cdx.url == url
    assert resp.revisit_cdx
    assert resp.revisit_cdx.url != url

    file_meta = gen_file_metadata(resp.body)
    assert file_meta['sha1hex'] == resp.cdx.sha1hex

    # not revisit?
    url = "ftp://ftp.cs.utexas.edu/pub/qsim/papers/Xu-crv-08.pdf"
    resp = wayback_client.lookup_resource(url)

    assert resp.hit == True
    assert resp.status == "success"
    assert resp.terminal_url == url
    assert resp.terminal_status_code == 226
    assert resp.cdx.url == url

    file_meta = gen_file_metadata(resp.body)
    assert file_meta['sha1hex'] == resp.cdx.sha1hex


@pytest.mark.skip(reason="hits prod services, requires auth")
def test_crawl_ftp(spn_client, wayback_client):

    url = "ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_pdf/ad/ab/mmr-17-05-6969.PMC5928650.pdf"
    resp = spn_client.crawl_resource(url, wayback_client)

    # FTP isn't supported yet!
    #assert resp.hit == True
    #assert resp.status == "success"
    #assert resp.terminal_url == url
    #assert resp.cdx.url == url

    assert resp.hit == False
    assert resp.status == "spn2-no-ftp"
