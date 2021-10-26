import struct

import pytest
import responses
from test_wayback import cdx_client, wayback_client

from sandcrawler import BlackholeSink, CdxLinePusher, GrobidClient, GrobidWorker, WaybackClient

FAKE_PDF_BYTES = b"%PDF SOME JUNK" + struct.pack("!q", 112853843)

with open('tests/files/23b29ea36382680716be08fc71aa81bd226e8a85.xml', 'rb') as f:
    REAL_TEI_XML = f.read()


@pytest.fixture
def grobid_client():
    client = GrobidClient(host_url="http://dummy-grobid", )
    return client


@responses.activate
def test_grobid_503(grobid_client):

    status = b'{"status": "done broke due to 503"}'
    responses.add(responses.POST,
                  'http://dummy-grobid/api/processFulltextDocument',
                  status=503,
                  body=status)

    resp = grobid_client.process_fulltext(FAKE_PDF_BYTES)

    # grobid gets POST 1x times
    assert len(responses.calls) == 1

    assert resp['status_code'] == 503
    assert resp['status'] == "error"


@responses.activate
def test_grobid_success(grobid_client):

    responses.add(responses.POST,
                  'http://dummy-grobid/api/processFulltextDocument',
                  status=200,
                  body=REAL_TEI_XML,
                  content_type='text/xml')

    resp = grobid_client.process_fulltext(FAKE_PDF_BYTES)

    # grobid gets POST 1x times
    assert len(responses.calls) == 1

    assert resp['status_code'] == 200
    assert resp['status'] == "success"
    #print(type(resp['tei_xml']))
    #print(type(REAL_TEI_XML))
    assert resp['tei_xml'] == REAL_TEI_XML.decode('ISO-8859-1')


@responses.activate
def test_grobid_worker_cdx(grobid_client, wayback_client):

    sink = BlackholeSink()
    worker = GrobidWorker(grobid_client, wayback_client, sink=sink)

    responses.add(responses.POST,
                  'http://dummy-grobid/api/processFulltextDocument',
                  status=200,
                  body=REAL_TEI_XML,
                  content_type='text/xml')

    with open('tests/files/example.cdx', 'r') as cdx_file:
        pusher = CdxLinePusher(
            worker,
            cdx_file,
            filter_http_statuses=[200, 226],
            filter_mimetypes=['application/pdf'],
        )
        pusher_counts = pusher.run()
        assert pusher_counts['total']
        assert pusher_counts['pushed'] == 7
        assert pusher_counts['pushed'] == worker.counts['total']

    assert len(responses.calls) == worker.counts['total']
