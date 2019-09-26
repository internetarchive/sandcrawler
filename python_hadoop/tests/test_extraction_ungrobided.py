
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
def test_mapper_single_line(mock_fetch, job):

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
    # file:mime should actually not get clobbered by GROBID updater
    #assert row[b'file:mime'] == b"application/pdf"
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

@mock.patch('extraction_ungrobided.MRExtractUnGrobided.fetch_warc_content', return_value=(FAKE_PDF_BYTES, None))
@responses.activate
def test_mapper_lines(mock_fetch, job):

    responses.add(responses.POST, 'http://localhost:8070/api/processFulltextDocument', status=200,
        body=REAL_TEI_XML, content_type='text/xml')

    raw = io.BytesIO(b"""sha1:23PTUXWSNSVE4HS5J7ELDUUG63J2FPCI\t{"c": 1, "d": "2016-06-09T00:27:36", "f": "WIDE-20160609001810-06993.warc.gz", "o": 287880616, "u": "http://www.case-research.eu/sites/default/files/publications/18092393_E-brief_Dabrowski_Monetary_Policy_final_0.pdf"}\tapplication/pdf\t{"c_size": 68262, "dt": "20160609002736", "offset": 287880616, "surt": "eu,case-research)/sites/default/files/publications/18092393_e-brief_dabrowski_monetary_policy_final_0.pdf", "url": "http://www.case-research.eu/sites/default/files/publications/18092393_E-brief_Dabrowski_Monetary_Policy_final_0.pdf", "warc": "WIDE-20160609000312-crawl427/WIDE-20160609001810-06993.warc.gz"}
sha1:23PW2APYHNBPIBRIVNQ6TMKUNY53UL3D\t{"c": 1, "d": "2016-01-07T03:29:03", "f": "MUSEUM-20160107025230-02354.warc.gz", "o": 413484441, "u": "http://www.portlandoregon.gov/fire/article/363695"}\tapplication/pdf\t{"c_size": 44600, "dt": "20160107032903", "offset": 413484441, "surt": "gov,portlandoregon)/fire/article/363695", "url": "http://www.portlandoregon.gov/fire/article/363695", "warc": "MUSEUM-20160107004301-crawl891/MUSEUM-20160107025230-02354.warc.gz"}
sha1:23RJIHUIOYY5747CR6YYCTMACXDCFYTT\t{"c": 1, "d": "2014-06-07T18:00:56", "f": "ARCHIVEIT-219-QUARTERLY-20047-20140607125555378-00017-wbgrp-crawl051.us.archive.org-6442.warc.gz", "o": 720590380, "u": "https://www.indiana.edu/~orafaq/faq/pdf.php?cat=36&id=264&artlang=en"}\tapplication/pdf\t{"c_size": 3727, "dt": "20140607180056", "offset": 720590380, "surt": "edu,indiana)/~orafaq/faq/pdf.php?artlang=en&cat=36&id=264", "url": "https://www.indiana.edu/~orafaq/faq/pdf.php?cat=36&id=264&artlang=en", "warc": "ARCHIVEIT-219-QUARTERLY-20047-00001/ARCHIVEIT-219-QUARTERLY-20047-20140607125555378-00017-wbgrp-crawl051.us.archive.org-6442.warc.gz"}""")


    output = io.BytesIO()
    job.sandbox(stdin=raw, stdout=output)

    job.run_mapper()

    # for debugging tests
    #print(output.getvalue().decode('utf-8'))
    #print(list(job.hb_table.scan()))

    # grobid gets POST 3x times
    assert len(responses.calls) == 3

    # wayback gets FETCH 3x times
    mock_fetch.assert_has_calls((
        mock.call("WIDE-20160609000312-crawl427/WIDE-20160609001810-06993.warc.gz", 287880616, 68262),
        mock.call("MUSEUM-20160107004301-crawl891/MUSEUM-20160107025230-02354.warc.gz", 413484441, 44600),
        mock.call("ARCHIVEIT-219-QUARTERLY-20047-00001/ARCHIVEIT-219-QUARTERLY-20047-20140607125555378-00017-wbgrp-crawl051.us.archive.org-6442.warc.gz", 720590380, 3727),
    ))

    # Saved extraction info
    assert job.hb_table.row(b'sha1:3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ') == {}
    assert job.hb_table.row(b'sha1:23PTUXWSNSVE4HS5J7ELDUUG63J2FPCI') != {}
    assert job.hb_table.row(b'sha1:23PW2APYHNBPIBRIVNQ6TMKUNY53UL3D') != {}
    assert job.hb_table.row(b'sha1:23RJIHUIOYY5747CR6YYCTMACXDCFYTT') != {}

    row = job.hb_table.row(b'sha1:23RJIHUIOYY5747CR6YYCTMACXDCFYTT')
    assert struct.unpack("!q", row[b'file:size'])[0] == len(FAKE_PDF_BYTES)
    # file:mime should actually not get clobbered by GROBID updater
    #assert row[b'file:mime'] == b"application/pdf"
    assert struct.unpack("!q", row[b'grobid0:status_code'])[0] == 200
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
    info, status = job.parse_ungrobided_line(raw)
    assert info is None
    assert status['status'] == "invalid"
    assert 'prefix' in status['reason']

    print("commented line")
    raw = "#com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 200 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz"
    info, status = job.parse_ungrobided_line(raw)
    assert info is None
    assert status['status'] == "invalid"
    assert 'prefix' in status['reason']

    print("wrong column count")
    raw = "a b c d e"
    info, status = job.parse_ungrobided_line(raw)
    assert info is None
    assert status['status'] == "invalid"
    assert 'parse' in status['reason']

    print("CDX line, somehow")
    raw = "com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf - 200 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz"
    info, status = job.parse_ungrobided_line(raw)
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
