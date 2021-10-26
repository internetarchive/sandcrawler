import json

import pytest
import responses

from sandcrawler import CdxApiClient, WaybackClient

CDX_TARGET = "http://fatcat.wiki/"
CDX_DT = "20180812220054"
# cdx -m exact -p output=json -p from=20180812220054 -p to=20180812220054 http://fatcat.wiki/
CDX_SINGLE_HIT = [
    [
        "urlkey", "timestamp", "original", "mimetype", "statuscode", "digest", "redirect",
        "robotflags", "length", "offset", "filename"
    ],
    [
        "wiki,fatcat)/", CDX_DT, CDX_TARGET, "text/html", "200",
        "O5RHV6OQ7SIHDJIEP7ZW53DLRX5NFIJR", "-", "-", "8445", "108062304",
        "WIDE-20180810142205-crawl802/WIDE-20180812131623-00059.warc.gz"
    ],
]

CDX_BEST_SHA1B32 = "AAAAAAAAASIHDJIEP7ZW53DLRX5NFIJR"
# cdx -m exact -p output=json -p from=20180812220054 -p to=20180812220054 http://fatcat.wiki/
CDX_MULTI_HIT = [
    [
        "urlkey", "timestamp", "original", "mimetype", "statuscode", "digest", "redirect",
        "robotflags", "length", "offset", "filename"
    ],
    [
        "wiki,fatcat)/", CDX_DT, CDX_TARGET, "text/html", "200",
        "O5RHV6OQ7SIHDJIEP7ZW53DLRX5NFIJR", "-", "-", "8445", "108062304",
        "WIDE-20180810142205-crawl802/WIDE-20180812131623-00059.warc.gz"
    ],
    # sooner, but not right mimetype
    [
        "wiki,fatcat)/", "20180912220054", CDX_TARGET, "text/html", "200",
        "O5RHV6OQ7SIHDJIEP7ZW53DLRX5NFIJR", "-", "-", "8445", "108062304",
        "WIDE-20180810142205-crawl802/WIDE-20180812131623-00059.warc.gz"
    ],
    # sooner and mimetype, but wrong status code
    [
        "wiki,fatcat)/", "20180912220054", CDX_TARGET, "application/pdf", "400",
        "O5RHV6OQ7SIHDJIEP7ZW53DLRX5NFIJR", "-", "-", "8445", "108062304",
        "WIDE-20180810142205-crawl802/WIDE-20180812131623-00059.warc.gz"
    ],
    [
        "wiki,fatcat)/", "20180912220054", CDX_TARGET, "application/pdf", "500",
        "O5RHV6OQ7SIHDJIEP7ZW53DLRX5NFIJR", "-", "-", "8445", "108062304",
        "WIDE-20180810142205-crawl802/WIDE-20180812131623-00059.warc.gz"
    ],
    [
        "wiki,fatcat)/", "20180912220054", CDX_TARGET, "application/pdf", "150",
        "O5RHV6OQ7SIHDJIEP7ZW53DLRX5NFIJR", "-", "-", "8445", "108062304",
        "WIDE-20180810142205-crawl802/WIDE-20180812131623-00059.warc.gz"
    ],
    # "best"
    [
        "wiki,fatcat)/", CDX_DT, CDX_TARGET, "application/pdf", "200", CDX_BEST_SHA1B32, "-",
        "-", "8445", "108062304",
        "WIDE-20180810142205-crawl802/WIDE-20180812131623-00059.warc.gz"
    ],
    # older
    [
        "wiki,fatcat)/", "20180712220054", CDX_TARGET, "application/pdf", "200",
        "O5RHV6OQ7SIHDJIEP7ZW53DLRX5NFIJR", "-", "-", "8445", "108062304",
        "WIDE-20180810142205-crawl802/WIDE-20180812131623-00059.warc.gz"
    ],
]


@pytest.fixture
def cdx_client():
    client = CdxApiClient(
        host_url="http://dummy-cdx/cdx",
        cdx_auth_token="dummy-token",
    )
    return client


@responses.activate
def test_cdx_fetch(cdx_client):

    responses.add(responses.GET,
                  'http://dummy-cdx/cdx',
                  status=200,
                  body=json.dumps(CDX_SINGLE_HIT))

    resp = cdx_client.fetch(CDX_TARGET, CDX_DT)

    assert len(responses.calls) == 1

    assert resp.datetime == CDX_DT
    assert resp.url == CDX_TARGET
    assert resp.sha1b32 == "O5RHV6OQ7SIHDJIEP7ZW53DLRX5NFIJR"
    assert resp.warc_csize == 8445
    assert resp.warc_offset == 108062304
    assert resp.warc_path == "WIDE-20180810142205-crawl802/WIDE-20180812131623-00059.warc.gz"


@responses.activate
def test_cdx_fetch_errors(cdx_client):

    with pytest.raises(ValueError):
        resp = cdx_client.fetch(CDX_TARGET, "2019")

    responses.add(responses.GET,
                  'http://dummy-cdx/cdx',
                  status=200,
                  body=json.dumps(CDX_SINGLE_HIT))

    with pytest.raises(KeyError):
        resp = cdx_client.fetch(CDX_TARGET, "20180812220055")

    with pytest.raises(KeyError):
        resp = cdx_client.fetch("http://some-other.com", CDX_DT)

    resp = cdx_client.fetch(CDX_TARGET, CDX_DT)
    assert len(responses.calls) == 3


@responses.activate
def test_cdx_lookup_best(cdx_client):

    responses.add(responses.GET,
                  'http://dummy-cdx/cdx',
                  status=200,
                  body=json.dumps(CDX_MULTI_HIT))

    resp = cdx_client.lookup_best(CDX_TARGET, best_mimetype="application/pdf")

    assert len(responses.calls) == 1

    assert resp.datetime == CDX_DT
    assert resp.url == CDX_TARGET
    assert resp.sha1b32 == CDX_BEST_SHA1B32
    assert resp.warc_path == CDX_SINGLE_HIT[1][-1]


WARC_TARGET = "http://fatcat.wiki/"
WARC_BODY = b"""
<html>
  <head>
      <meta name="citation_pdf_url" content="http://www.example.com/content/271/20/11761.full.pdf">
  </head>
  <body>
    <h1>my big article here</h1>
    blah
  </body>
</html>
"""


@pytest.fixture
def wayback_client(cdx_client, mocker):
    client = WaybackClient(
        cdx_client=cdx_client,
        petabox_webdata_secret="dummy-petabox-secret",
    )
    # mock out the wayback store with mock stuff
    client.rstore = mocker.Mock()
    resource = mocker.Mock()
    client.rstore.load_resource = mocker.MagicMock(return_value=resource)
    resource.get_status = mocker.MagicMock(return_value=(200, "Ok"))
    resource.is_revisit = mocker.MagicMock(return_value=False)
    resource.get_location = mocker.MagicMock(return_value=WARC_TARGET)
    body = mocker.Mock()
    resource.open_raw_content = mocker.MagicMock(return_value=body)
    body.read = mocker.MagicMock(return_value=WARC_BODY)

    return client


@pytest.fixture
def wayback_client_pdf(cdx_client, mocker):

    with open('tests/files/dummy.pdf', 'rb') as f:
        pdf_bytes = f.read()

    client = WaybackClient(
        cdx_client=cdx_client,
        petabox_webdata_secret="dummy-petabox-secret",
    )
    # mock out the wayback store with mock stuff
    client.rstore = mocker.Mock()
    resource = mocker.Mock()
    client.rstore.load_resource = mocker.MagicMock(return_value=resource)
    resource.get_status = mocker.MagicMock(return_value=(200, "Ok"))
    resource.is_revisit = mocker.MagicMock(return_value=False)
    resource.get_location = mocker.MagicMock(return_value=WARC_TARGET)
    body = mocker.Mock()
    resource.open_raw_content = mocker.MagicMock(return_value=body)
    body.read = mocker.MagicMock(return_value=pdf_bytes)

    return client


@responses.activate
def test_wayback_fetch(wayback_client):
    resp = wayback_client.fetch_petabox(123, 456789, "here/there.warc.gz")
    assert resp.body == WARC_BODY
    assert resp.location == WARC_TARGET

    resp = wayback_client.fetch_petabox_body(123, 456789, "here/there.warc.gz")
    assert resp == WARC_BODY


@responses.activate
def test_lookup_resource_success(wayback_client):

    responses.add(responses.GET,
                  'http://dummy-cdx/cdx',
                  status=200,
                  body=json.dumps(CDX_MULTI_HIT))

    resp = wayback_client.lookup_resource(CDX_TARGET)

    assert resp.hit is True
