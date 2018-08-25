
import io
import json
import mrjob
import pytest
import struct
import responses
import happybase_mock
import wayback.exception
from unittest import mock
from common import parse_ungrobided_line
from extraction_ungrobided import MRExtractUnGrobided


FAKE_PDF_BYTES = b"%PDF SOME JUNK" + struct.pack("!q", 112853843)
OK_UNGROBIDED_LINE = b"\t".join((
    b"sha1:3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ",
    b"""{"c": 1, "d": "2017-07-06T07:54:11", "f": "CITESEERX-CRAWL-2017-06-20-20170706075012840-00388-3671~wbgrp-svc285.us.archive.org~8443.warc.gz", "o": 914718776, "u": "http://www.ibc7.org/article/file_down.php?mode%3Darticle_print%26pid%3D250"}""",
    b"application/pdf",
    b"""{"c_size": 501, "dt": "20170706075411", "offset": 914718776, "surt": "org,ibc7)/article/file_down.php?mode=article_print&pid=250", "url": "http://www.ibc7.org/article/file_down.php?mode%3Darticle_print%26pid%3D250", "warc": "CITESEERX-CRAWL-2017-06-20-20170706074206206-00379-00388-wbgrp-svc285/CITESEERX-CRAWL-2017-06-20-20170706075012840-00388-3671~wbgrp-svc285.us.archive.org~8443.warc.gz"}""",
))

with open('tests/files/23b29ea36382680716be08fc71aa81bd226e8a85.xml', 'r') as f:
    REAL_TEI_XML = f.read()

@pytest.fixture
def job():
    """
    Note: this mock only seems to work with job.run_mapper(), not job.run();
    the later results in a separate instantiation without the mock?
    """
    job = MRExtractUnGrobided(['--no-conf', '-'])

    conn = happybase_mock.Connection()
    conn.create_table('wbgrp-journal-extract-test',
        {'file': {}, 'grobid0': {}, 'f': {}})
    job.hb_table = conn.table('wbgrp-journal-extract-test')

    return job


@mock.patch('extraction_ungrobided.MRExtractUnGrobided.fetch_warc_content', return_value=(FAKE_PDF_BYTES, None))
@responses.activate
def test_mapper_lines(mock_fetch, job):

    responses.add(responses.POST, 'http://localhost:8070/api/processFulltextDocument', status=200,
        body=REAL_TEI_XML, content_type='text/xml')

    raw = io.BytesIO(OK_UNGROBIDED_LINE)

    output = io.BytesIO()
    job.sandbox(stdin=raw, stdout=output)

    job.run_mapper()

    # for debugging tests
    #print(output.getvalue().decode('utf-8'))
    #print(list(job.hb_table.scan()))

    # wayback gets FETCH 1x times
    mock_fetch.assert_called_once_with(
        "CITESEERX-CRAWL-2017-06-20-20170706074206206-00379-00388-wbgrp-svc285/CITESEERX-CRAWL-2017-06-20-20170706075012840-00388-3671~wbgrp-svc285.us.archive.org~8443.warc.gz",
        914718776,
        501)

    # grobid gets POST 1x times
    assert len(responses.calls) == 1

    # HBase
    assert job.hb_table.row(b'1') == {}

    # Saved extraction info
    row = job.hb_table.row(b'sha1:3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ')

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

def test_parse_ungrobided_invalid(job):

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
    raw = "a b c d e"
    info, status = job.parse_line(raw)
    assert info is None
    assert status['status'] == "invalid"
    assert 'parse' in status['reason']

    print("CDX line, somehow")
    raw = "com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf - 200 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz"
    info, status = job.parse_line(raw)
    assert info is None
    print(status)
    assert status['status'] == "invalid"
    assert 'parse' in status['reason']

def test_parse_ungrobided_valid():

    parsed = parse_ungrobided_line(OK_UNGROBIDED_LINE.decode('utf-8'))
    assert parsed['key'] == "sha1:3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ"
    assert parsed['f:c']['u'] == "http://www.ibc7.org/article/file_down.php?mode%3Darticle_print%26pid%3D250"
    assert parsed['file:mime'] == "application/pdf"
    assert parsed['file:cdx']['c_size'] == 501
    assert parsed['file:cdx']['dt'] == "20170706075411"
