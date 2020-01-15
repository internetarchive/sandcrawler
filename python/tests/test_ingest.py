
import json
import pytest
import responses

from sandcrawler import *
from test_wayback import *
from test_savepagenow import *
from test_grobid import REAL_TEI_XML


@pytest.fixture
def ingest_worker(wayback_client, spn_client):
    grobid_client = GrobidClient(
        host_url="http://dummy-grobid",
    )
    worker = IngestFileWorker(
        wayback_client=wayback_client,
        spn_client=spn_client,
        grobid_client=grobid_client,
    )
    return worker

@pytest.fixture
def ingest_worker_pdf(wayback_client_pdf, spn_client):
    grobid_client = GrobidClient(
        host_url="http://dummy-grobid",
    )
    pgrest_client = SandcrawlerPostgrestClient(
        api_url="http://dummy-postgrest",
    )
    worker = IngestFileWorker(
        wayback_client=wayback_client_pdf,
        spn_client=spn_client,
        grobid_client=grobid_client,
        pgrest_client=pgrest_client,
    )
    return worker


@responses.activate
def test_ingest_success(ingest_worker_pdf):

    with open('tests/files/dummy.pdf', 'rb') as f:
        pdf_bytes = f.read()

    request = {
        'ingest_type': 'pdf',
        'base_url': "http://dummy-host/",
    }
    responses.add(responses.POST,
        'http://dummy-spnv2/save',
        status=200,
        body=json.dumps({"url": TARGET, "job_id": JOB_ID}))
    responses.add(responses.GET,
        'http://dummy-spnv2/save/status/' + JOB_ID,
        status=200,
        body=json.dumps(PENDING_BODY))
    responses.add(responses.GET,
        'http://dummy-spnv2/save/status/' + JOB_ID,
        status=200,
        body=json.dumps(SUCCESS_BODY))
    responses.add(responses.GET,
        'http://dummy-cdx/cdx',
        status=200,
        body=json.dumps(CDX_SPN_HIT))
    responses.add(responses.GET,
        'https://web.archive.org/web/{}id_/{}'.format("20180326070330", TARGET + "/redirect"),
        status=200,
        headers={"X-Archive-Src": "liveweb-whatever.warc.gz"},
        body=pdf_bytes)
    responses.add(responses.GET,
        'http://dummy-postgrest/grobid?sha1hex=eq.{}'.format("90ffd2359008d82298821d16b21778c5c39aec36"),
        status=200,
        body=json.dumps([]))
    responses.add(responses.POST,
        'http://dummy-grobid/api/processFulltextDocument', status=200,
        body=REAL_TEI_XML, content_type='text/xml')

    resp = ingest_worker_pdf.process(request)

    print(resp)
    assert resp['hit'] == True
    assert resp['status'] == "success"
    assert resp['request'] == request
    assert resp['file_meta']['size_bytes']
    assert resp['grobid']
    assert not 'tei_xml' in resp['grobid']
    assert resp['terminal']

@responses.activate
def test_ingest_landing(ingest_worker):

    request = {
        'ingest_type': 'pdf',
        'base_url': "http://dummy-host/",
    }
    responses.add(responses.POST,
        'http://dummy-spnv2/save',
        status=200,
        body=json.dumps({"url": TARGET, "job_id": JOB_ID}))
    responses.add(responses.GET,
        'http://dummy-spnv2/save/status/' + JOB_ID,
        status=200,
        body=json.dumps(PENDING_BODY))
    responses.add(responses.GET,
        'http://dummy-spnv2/save/status/' + JOB_ID,
        status=200,
        body=json.dumps(SUCCESS_BODY))
    responses.add(responses.GET,
        'http://dummy-cdx/cdx',
        status=200,
        body=json.dumps(CDX_SPN_HIT))
    responses.add(responses.GET,
        'https://web.archive.org/web/{}id_/{}'.format("20180326070330", TARGET + "/redirect"),
        status=200,
        headers={"X-Archive-Src": "liveweb-whatever.warc.gz"},
        body=WARC_BODY)

    # this is for second time around; don't want to fetch same landing page
    # HTML again and result in a loop
    responses.add(responses.GET,
        'https://web.archive.org/web/{}id_/{}'.format("20180326070330", TARGET + "/redirect"),
        status=200,
        headers={"X-Archive-Src": "liveweb-whatever.warc.gz"},
        body="<html></html>")

    resp = ingest_worker.process(request)

    print(resp)
    assert resp['hit'] == False
    assert resp['status'] == "no-pdf-link"
    assert resp['request'] == request
    assert 'grobid' not in resp

