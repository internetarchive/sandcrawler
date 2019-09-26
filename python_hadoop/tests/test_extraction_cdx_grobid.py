
import io
import json
import mrjob
import pytest
import struct
import responses
import happybase_mock
import wayback.exception
from unittest import mock
from extraction_cdx_grobid import MRExtractCdxGrobid


FAKE_PDF_BYTES = b"%PDF SOME JUNK" + struct.pack("!q", 112853843)
OK_CDX_LINE = b"""com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 200 ABCDEF12345Q2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz"""

with open('tests/files/23b29ea36382680716be08fc71aa81bd226e8a85.xml', 'r') as f:
    REAL_TEI_XML = f.read()

@pytest.fixture
def job():
    """
    Note: this mock only seems to work with job.run_mapper(), not job.run();
    the later results in a separate instantiation without the mock?
    """
    job = MRExtractCdxGrobid(['--no-conf', '-'])

    conn = happybase_mock.Connection()
    conn.create_table('wbgrp-journal-extract-test',
        {'file': {}, 'grobid0': {}, 'f': {}})
    job.hb_table = conn.table('wbgrp-journal-extract-test')

    return job


@mock.patch('extraction_cdx_grobid.MRExtractCdxGrobid.fetch_warc_content', return_value=(FAKE_PDF_BYTES, None))
@responses.activate
def test_mapper_lines(mock_fetch, job):

    responses.add(responses.POST, 'http://localhost:8070/api/processFulltextDocument', status=200,
        body=REAL_TEI_XML, content_type='text/xml')

    raw = io.BytesIO(b"""
com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 301 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz
eu,eui,cadmus)/bitstream/handle/1814/36635/rscas_2015_03.pdf;jsessionid=761393014319a39f40d32ae3eb3a853f?sequence=1 20170705062202 http://cadmus.eui.eu/bitstream/handle/1814/36635/RSCAS_2015_03.pdf%3Bjsessionid%3D761393014319A39F40D32AE3EB3A853F?sequence%3D1 application/PDF 200 MPCXVWMUTRUGFP36SLPHKDLY6NGU4S3J - - 854156 328850624 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz
com,pbworks,educ333b)/robots.txt 20170705063311 http://educ333b.pbworks.com/robots.txt text/plain 200 6VAUYENMOU2SK2OWNRPDD6WTQTECGZAD - - 638 398190140 CITESEERX-CRAWL-2017-06-20-20170705062707827-00049-00058-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705063158203-00053-31209~wbgrp-svc284.us.archive.org~8443.warc.gz
""")

    output = io.BytesIO()
    job.sandbox(stdin=raw, stdout=output)

    job.run_mapper()

    # for debugging tests
    #print(output.getvalue().decode('utf-8'))
    #print(list(job.hb_table.scan()))

    # wayback gets FETCH 1x times
    mock_fetch.assert_called_once_with(
        "CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz",
        328850624,
        854156)

    # grobid gets POST 1x times
    assert len(responses.calls) == 1

    # HBase
    assert job.hb_table.row(b'1') == {}
    # HTTP 301
    assert job.hb_table.row(b'sha1:3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ') == {}
    # valid
    assert job.hb_table.row(b'sha1:MPCXVWMUTRUGFP36SLPHKDLY6NGU4S3J') != {}
    # text/plain
    assert job.hb_table.row(b'sha1:6VAUYENMOU2SK2OWNRPDD6WTQTECGZAD') == {}

    # Saved extraction info
    row = job.hb_table.row(b'sha1:MPCXVWMUTRUGFP36SLPHKDLY6NGU4S3J')

    assert struct.unpack("!q", row[b'file:size'])[0] == len(FAKE_PDF_BYTES)
    assert row[b'file:mime'] == b"application/pdf"
    assert struct.unpack("!q", row[b'grobid0:status_code'])[0] == 200
    # TODO: assert row[b'grobid0:quality'] == None
    status = json.loads(row[b'grobid0:status'].decode('utf-8'))
    assert type(status) == type(dict())
    assert row[b'grobid0:tei_xml'].decode('utf-8') == REAL_TEI_XML
    tei_json = json.loads(row[b'grobid0:tei_json'].decode('utf-8'))
    metadata = json.loads(row[b'grobid0:metadata'].decode('utf-8'))
    assert tei_json['title'] == metadata['title']
    assert 'body' in tei_json
    assert 'body' not in metadata

def test_parse_cdx_invalid(job):

    print("valid")
    raw = "com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 200 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz"
    info, status = job.parse_line(raw)
    assert status is None

    print("space-prefixed line")
    raw = " com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 200 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz"
    info, status = job.parse_line(raw)
    assert info is None
    assert status['status'] == "invalid"
    assert 'prefix' in status['reason']

    print("commented line")
    raw = "#com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 200 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz"
    info, status = job.parse_line(raw)
    assert info is None
    assert status['status'] == "invalid"
    assert 'prefix' in status['reason']

    print("wrong column count")
    raw = "a b c d"
    info, status = job.parse_line(raw)
    assert info is None
    assert status['status'] == "invalid"
    assert 'parse' in status['reason']

    print("missing mimetype")
    raw = "com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf - 200 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz"
    info, status = job.parse_line(raw)
    assert info is None
    print(status)
    assert status['status'] == "invalid"
    assert 'parse' in status['reason']

    print("HTTP status")
    raw = "com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 501 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz"
    info, status = job.parse_line(raw)
    assert info is None
    assert status['status'] == "invalid"

    print("datetime")
    raw = "com,sagepub,cep)/content/28/9/960.full.pdf 20170705 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 501 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz"
    info, status = job.parse_line(raw)
    assert info is None
    assert status['status'] == "invalid"


def test_parse_cdx_skip(job):

    job.mapper_init()

    print("warc format")
    raw = "com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 200 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz"
    info, status = job.mapper(None, raw).__next__()
    assert info is None
    assert status['status'] == "skip"
    assert 'WARC' in status['reason']

    print("mimetype")
    raw = "com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf text/html 200 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz"
    info, status = job.mapper(None, raw).__next__()
    assert info is None
    assert status['status'] == "skip"
    assert 'mimetype' in status['reason']


@mock.patch('extraction_cdx_grobid.MRExtractCdxGrobid.fetch_warc_content', return_value=(FAKE_PDF_BYTES, None))
@responses.activate
def test_grobid_503(mock_fetch, job):

    status = b'{"status": "done broke due to 503"}'
    responses.add(responses.POST, 'http://localhost:8070/api/processFulltextDocument', status=503,
        body=status)

    output = io.BytesIO()
    job.sandbox(stdin=io.BytesIO(OK_CDX_LINE), stdout=output)
    job.run_mapper()
    row = job.hb_table.row(b'sha1:ABCDEF12345Q2MSVX7XZKYAYSCX5QBYJ')
    status = json.loads(row[b'grobid0:status'].decode('utf-8'))
    assert json.loads(row[b'grobid0:status'].decode('utf-8')) == status


@mock.patch('extraction_cdx_grobid.MRExtractCdxGrobid.fetch_warc_content', return_value=(FAKE_PDF_BYTES, None))
@responses.activate
def test_grobid_not_xml(mock_fetch, job):

    payload = b'this is not XML'
    responses.add(responses.POST, 'http://localhost:8070/api/processFulltextDocument', status=200,
        body=payload)

    output = io.BytesIO()
    job.sandbox(stdin=io.BytesIO(OK_CDX_LINE), stdout=output)
    job.run_mapper()
    output = output.getvalue().decode('utf-8')
    row = job.hb_table.row(b'sha1:ABCDEF12345Q2MSVX7XZKYAYSCX5QBYJ')
    assert struct.unpack("!q", row[b'grobid0:status_code'])[0] == 200
    assert row[b'grobid0:tei_xml'] == payload
    assert b'grobid0:tei_json' not in row
    assert "XML parse error" in output


@mock.patch('extraction_cdx_grobid.MRExtractCdxGrobid.fetch_warc_content', return_value=(FAKE_PDF_BYTES, None))
@responses.activate
def test_grobid_not_tei(mock_fetch, job):

    payload = b'<xml></xml>'
    responses.add(responses.POST, 'http://localhost:8070/api/processFulltextDocument', status=200,
        body=payload)

    output = io.BytesIO()
    job.sandbox(stdin=io.BytesIO(OK_CDX_LINE), stdout=output)
    job.run_mapper()
    output = output.getvalue().decode('utf-8')
    row = job.hb_table.row(b'sha1:ABCDEF12345Q2MSVX7XZKYAYSCX5QBYJ')
    assert struct.unpack("!q", row[b'grobid0:status_code'])[0] == 200
    assert row[b'grobid0:tei_xml'] == payload
    assert b'grobid0:tei_json' not in row
    assert "non-TEI content" in output


@mock.patch('extraction_cdx_grobid.MRExtractCdxGrobid.fetch_warc_content', return_value=(FAKE_PDF_BYTES, None))
def test_grobid_invalid_connection(mock_fetch, job):

    status = b'{"status": "done broke"}'
    job.options.grobid_uri = 'http://host.invalid:8070/api/processFulltextDocument'

    output = io.BytesIO()
    job.sandbox(stdin=io.BytesIO(OK_CDX_LINE), stdout=output)
    job.run_mapper()
    output = output.getvalue().decode('utf-8')
    assert 'error' in output
    assert 'GROBID' in output
    assert job.hb_table.row(b'sha1:ABCDEF12345Q2MSVX7XZKYAYSCX5QBYJ') == {}


def test_wayback_failure(job):

    job.options.warc_uri_prefix = 'http://host.invalid/'

    output = io.BytesIO()
    job.sandbox(stdin=io.BytesIO(OK_CDX_LINE), stdout=output)
    job.run_mapper()
    output = output.getvalue().decode('utf-8')
    assert 'error' in output
    assert 'wayback' in output
    assert job.hb_table.row(b'sha1:ABCDEF12345Q2MSVX7XZKYAYSCX5QBYJ') == {}


@mock.patch('extraction_cdx_grobid.ResourceStore')
def test_wayback_not_found(mock_rs, job):

    # This is... a little convoluded. Basically creating a 404 situation for
    # reading a wayback resource.
    mock_resource = mock.MagicMock()
    mock_resource.get_status.return_value = (404, "Not Found")
    mock_rso = mock.MagicMock()
    mock_rso.load_resource.return_value = mock_resource
    mock_rs.return_value = mock_rso
    print(mock_rs().load_resource().get_status())

    job.options.warc_uri_prefix = 'http://dummy-archive.org/'

    output = io.BytesIO()
    job.sandbox(stdin=io.BytesIO(OK_CDX_LINE), stdout=output)
    job.run_mapper()
    output = output.getvalue().decode('utf-8')

    print(output)
    assert 'error' in output
    assert 'not 200' in output
    assert job.hb_table.row(b'sha1:ABCDEF12345Q2MSVX7XZKYAYSCX5QBYJ') == {}


@mock.patch('extraction_cdx_grobid.MRExtractCdxGrobid.fetch_warc_content', return_value=(FAKE_PDF_BYTES, None))
@responses.activate
def test_mapper_rerun(mock_fetch, job):

    responses.add(responses.POST, 'http://localhost:8070/api/processFulltextDocument', status=200,
        body=REAL_TEI_XML, content_type='text/xml')

    output1 = io.BytesIO()
    job.sandbox(stdin=io.BytesIO(OK_CDX_LINE), stdout=output1)
    job.run_mapper()
    output1 = output1.getvalue().decode('utf-8')

    # wayback gets FETCH 1x times
    assert mock_fetch.call_count == 1
    # grobid gets POST 1x times
    assert len(responses.calls) == 1
    # HBase
    assert job.hb_table.row(b'sha1:ABCDEF12345Q2MSVX7XZKYAYSCX5QBYJ') != {}
    assert 'success' in output1

    # Run again, same line
    output2 = io.BytesIO()
    job.sandbox(stdin=io.BytesIO(OK_CDX_LINE), stdout=output2)
    job.run_mapper()
    output2 = output2.getvalue().decode('utf-8')

    # wayback still only FETCH 1x times
    assert mock_fetch.call_count == 1
    # grobid still only POST 1x times
    assert len(responses.calls) == 1
    assert 'existing' in output2

@mock.patch('extraction_cdx_grobid.MRExtractCdxGrobid.fetch_warc_content', return_value=(FAKE_PDF_BYTES, None))
@responses.activate
def test_mapper_previously_backfilled(mock_fetch, job):

    responses.add(responses.POST, 'http://localhost:8070/api/processFulltextDocument', status=200,
        body=REAL_TEI_XML, content_type='text/xml')

    job.hb_table.put(b'sha1:ABCDEF12345Q2MSVX7XZKYAYSCX5QBYJ',
        {b'f:c': b'{"some": "dict"}', b'file:col': b'bogus'})
    assert job.hb_table.row(b'sha1:ABCDEF12345Q2MSVX7XZKYAYSCX5QBYJ') != {}

    output1 = io.BytesIO()
    job.sandbox(stdin=io.BytesIO(OK_CDX_LINE), stdout=output1)
    job.run_mapper()
    output1 = output1.getvalue().decode('utf-8')

    # wayback gets FETCH 1x times
    assert mock_fetch.call_count == 1
    # grobid gets POST 1x times
    assert len(responses.calls) == 1
    assert 'success' in output1
