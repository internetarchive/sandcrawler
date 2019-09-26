
import pytest
import struct
import responses

from sandcrawler import GrobidClient, GrobidWorker, CdxLinePusher, BlackholeSink, WaybackClient


FAKE_PDF_BYTES = b"%PDF SOME JUNK" + struct.pack("!q", 112853843)

with open('tests/files/23b29ea36382680716be08fc71aa81bd226e8a85.xml', 'rb') as f:
    REAL_TEI_XML = f.read()

@responses.activate
def test_grobid_503():

    client = GrobidClient(host_url="http://localhost:8070")

    status = b'{"status": "done broke due to 503"}'
    responses.add(responses.POST,
        'http://localhost:8070/api/processFulltextDocument', status=503,
        body=status)

    resp = client.process_fulltext(FAKE_PDF_BYTES)

    # grobid gets POST 1x times
    assert len(responses.calls) == 1

    assert resp['status_code'] == 503
    assert resp['status'] == "error"

@responses.activate
@pytest.mark.skip(reason="XXX: need to fix unicode/bytes something something")
def test_grobid_success():

    client = GrobidClient(host_url="http://localhost:8070")

    responses.add(responses.POST,
        'http://localhost:8070/api/processFulltextDocument', status=200,
        body=REAL_TEI_XML, content_type='text/xml')

    resp = client.process_fulltext(FAKE_PDF_BYTES)

    # grobid gets POST 1x times
    assert len(responses.calls) == 1

    assert resp['status_code'] == 200
    assert resp['status'] == "success"
    print(type(resp['tei_xml']))
    print(type(REAL_TEI_XML))
    assert resp['tei_xml'] == REAL_TEI_XML.decode('utf-8')
    #assert resp['tei_xml'].split('\n')[:3] == REAL_TEI_XML.split('\n')[:3]

@responses.activate
def test_grobid_worker_cdx():

    sink = BlackholeSink()
    grobid_client = GrobidClient(host_url="http://localhost:8070")
    wayback_client = WaybackClient()
    worker = GrobidWorker(grobid_client, wayback_client, sink=sink)

    responses.add(responses.POST,
        'http://localhost:8070/api/processFulltextDocument', status=200,
        body=REAL_TEI_XML, content_type='text/xml')

    with open('tests/files/example.cdx', 'r') as cdx_file:
        pusher = CdxLinePusher(worker, cdx_file,
            filter_http_statuses=[200], filter_mimetypes=['application/pdf'])
        pusher_counts = pusher.run()
        assert pusher_counts['total']
        assert pusher_counts['pushed'] == 7
        assert pusher_counts['pushed'] == worker.counts['total']

    assert len(responses.calls) == worker.counts['total']

