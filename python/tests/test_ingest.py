import json

import pytest
import responses
from test_grobid import REAL_TEI_XML
from test_savepagenow import *
from test_wayback import *

from sandcrawler import *


@pytest.fixture
def ingest_worker(wayback_client, spn_client):
    grobid_client = GrobidClient(host_url="http://dummy-grobid", )
    worker = IngestFileWorker(
        wayback_client=wayback_client,
        spn_client=spn_client,
        grobid_client=grobid_client,
    )
    return worker


@pytest.fixture
def ingest_worker_pdf(wayback_client_pdf, spn_client):
    grobid_client = GrobidClient(host_url="http://dummy-grobid", )
    pgrest_client = SandcrawlerPostgrestClient(api_url="http://dummy-postgrest", )
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
                  body=json.dumps({
                      "url": TARGET,
                      "job_id": JOB_ID
                  }))
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
                  'https://web.archive.org/web/{}id_/{}'.format("20180326070330",
                                                                TARGET + "/redirect"),
                  status=200,
                  headers={"X-Archive-Src": "liveweb-whatever.warc.gz"},
                  body=pdf_bytes)
    responses.add(responses.GET,
                  'http://dummy-postgrest/grobid?sha1hex=eq.{}'.format(
                      "90ffd2359008d82298821d16b21778c5c39aec36"),
                  status=200,
                  body=json.dumps([]))
    responses.add(responses.GET,
                  'http://dummy-postgrest/pdf_meta?sha1hex=eq.{}'.format(
                      "90ffd2359008d82298821d16b21778c5c39aec36"),
                  status=200,
                  body=json.dumps([]))
    responses.add(responses.POST,
                  'http://dummy-grobid/api/processFulltextDocument',
                  status=200,
                  body=REAL_TEI_XML,
                  content_type='text/xml')

    resp = ingest_worker_pdf.process(request)

    print(resp)
    assert resp['hit'] is True
    assert resp['status'] == "success"
    assert resp['request'] == request
    assert resp['terminal']['terminal_sha1hex'] == resp['file_meta']['sha1hex']
    assert type(resp['terminal']['terminal_dt']) == str
    assert resp['terminal']['terminal_url'] == TARGET + "/redirect"
    assert resp['terminal']['terminal_status_code']
    assert type(resp['file_meta']['size_bytes']) == int
    assert resp['file_meta']['mimetype'] == "application/pdf"
    assert resp['cdx']['url'] == TARGET + "/redirect"
    assert 'warc_path' not in resp['cdx']
    assert 'revisit_cdx' not in resp
    assert resp['grobid']['status'] == "success"
    assert resp['grobid']['status_code'] == 200
    assert resp['grobid']['grobid_version']
    assert 'fatcat_release' in resp['grobid']
    assert 'grobid_version' not in resp['grobid']['metadata']
    assert 'fatcat_release' not in resp['grobid']['metadata']
    assert 'tei_xml' not in resp['grobid']
    assert resp['pdf_meta']['status'] == "success"
    assert resp['pdf_meta']['pdf_extra']['page_count'] == 1
    assert resp['pdf_meta'].get('text') is None


@responses.activate
def test_ingest_landing(ingest_worker):

    request = {
        'ingest_type': 'pdf',
        'base_url': "http://dummy-host/",
    }
    responses.add(responses.POST,
                  'http://dummy-spnv2/save',
                  status=200,
                  body=json.dumps({
                      "url": TARGET,
                      "job_id": JOB_ID
                  }))
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
                  'https://web.archive.org/web/{}id_/{}'.format("20180326070330",
                                                                TARGET + "/redirect"),
                  status=200,
                  headers={"X-Archive-Src": "liveweb-whatever.warc.gz"},
                  body=WARC_BODY)

    # this is for second time around; don't want to fetch same landing page
    # HTML again and result in a loop
    responses.add(responses.GET,
                  'https://web.archive.org/web/{}id_/{}'.format("20180326070330",
                                                                TARGET + "/redirect"),
                  status=200,
                  headers={"X-Archive-Src": "liveweb-whatever.warc.gz"},
                  body="<html></html>")

    resp = ingest_worker.process(request)

    print(resp)
    assert resp['hit'] is False
    assert resp['status'] == "no-pdf-link"
    assert resp['request'] == request
    assert 'terminal' in resp
    assert 'file_meta' not in resp
    assert 'cdx' not in resp
    assert 'revisit_cdx' not in resp
    assert 'grobid' not in resp


@responses.activate
def test_ingest_blocklist(ingest_worker):

    ingest_worker.base_url_blocklist = [
        '://test.fatcat.wiki/',
    ]
    request = {
        'ingest_type': 'pdf',
        'base_url': "https://test.fatcat.wiki/asdfasdf.pdf",
    }

    resp = ingest_worker.process(request)

    assert resp['hit'] is False
    assert resp['status'] == "skip-url-blocklist"
    assert resp['request'] == request


@responses.activate
def test_ingest_wall_blocklist(ingest_worker):

    ingest_worker.wall_blocklist = [
        '://test.fatcat.wiki/',
    ]
    request = {
        'ingest_type': 'pdf',
        'base_url': "https://test.fatcat.wiki/asdfasdf.pdf",
    }

    resp = ingest_worker.process(request)

    assert resp['hit'] is False
    assert resp['status'] == "skip-wall"
    assert resp['request'] == request


@responses.activate
def test_ingest_cookie_blocklist(ingest_worker):

    request = {
        'ingest_type': 'pdf',
        'base_url': "https://test.fatcat.wiki/cookieAbsent",
    }

    resp = ingest_worker.process(request)

    assert resp['hit'] is False
    assert resp['status'] == "blocked-cookie"
    assert resp['request'] == request
