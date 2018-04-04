
import io
import json
import pytest
import mrjob
import responses
import happybase_mock
from extraction_cdx_grobid import MRExtractCDXGROBID



def test_parse_cdx_line():

    raw = "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz"
    correct = {
        'key': "sha1:WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G",
        'file:mime': "application/pdf",
        'file:cdx': {
            'surt': "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf",
            'url': "https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf",
            'dt': "20170828233154",
            'warc': "SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz",
            'offset': 931661233,
            'c_size': 210251,
        },
        'f:c': {
            'u': "https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf",
            'd': "2017-08-28T23:31:54",
            'f': "SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz",
            'o': 931661233,
            'c': 1,
        }
    }

    assert transform_line(raw) == correct
    assert transform_line(raw + "\n") == correct
    assert transform_line(raw + " extra_field") == correct

@pytest.fixture
def job():
    """
    Note: this mock only seems to work with job.run_mapper(), not job.run();
    the later results in a separate instantiation without the mock?
    """
    conn = happybase_mock.Connection()
    conn.create_table('wbgrp-journal-extract-test',
        {'file': {}, 'grobid0': {}, 'f': {}})
    table = conn.table('wbgrp-journal-extract-test')

    job = MRCDXBackfillHBase(['--no-conf', '-'], hb_table=table)
    return job


@responses.activate
def test_mapper_lines(job):

    fake_grobid = {}
    responses.add(responses.POST, 'http://localhost:9070/api/processFulltextDocument', status=200,
        body=json.dumps(fake_grobid), content_type='application/json')

    raw = io.BytesIO(b"""
com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 301 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz
eu,eui,cadmus)/bitstream/handle/1814/36635/rscas_2015_03.pdf;jsessionid=761393014319a39f40d32ae3eb3a853f?sequence=1 20170705062202 http://cadmus.eui.eu/bitstream/handle/1814/36635/RSCAS_2015_03.pdf%3Bjsessionid%3D761393014319A39F40D32AE3EB3A853F?sequence%3D1 application/PDF 200 MPCXVWMUTRUGFP36SLPHKDLY6NGU4S3J - - 854156 328850624 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz
com,pbworks,educ333b)/robots.txt 20170705063311 http://educ333b.pbworks.com/robots.txt text/plain 200 6VAUYENMOU2SK2OWNRPDD6WTQTECGZAD - - 638 398190140 CITESEERX-CRAWL-2017-06-20-20170705062707827-00049-00058-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705063158203-00053-31209~wbgrp-svc284.us.archive.org~8443.warc.gz
""")

    job.sandbox(stdin=raw)
    job.run_mapper()

    # wayback gets FETCH 1x times

    # grobid gets POST 3x times

    # hbase 


    assert job.hb_table.row(b'1') == {}
    # HTTP 301
    assert job.hb_table.row(b'sha1:3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ') == {}
    # valid
    assert job.hb_table.row(b'sha1:MPCXVWMUTRUGFP36SLPHKDLY6NGU4S3J') != {}
    # text/plain
    assert job.hb_table.row(b'sha1:6VAUYENMOU2SK2OWNRPDD6WTQTECGZAD') == {}

    row = job.hb_table.row(b'sha1:MPCXVWMUTRUGFP36SLPHKDLY6NGU4S3J')

    assert struct.unpack("", row[b'file:size']) == 12345
    assert row[b'file:mime'] == b"application/pdf"
    assert struct.unpack("", row[b'grobid0:status_code']) == 200
    assert row[b'grobid0:quality'] == None # TODO
    status = json.loads(row[b'grobid0:status'].decode('utf-8'))
    assert type(row[b'grobid0:status']) == type(dict())
    assert row[b'grobid0:tei_xml'] == "<xml><lorem>ipsum</lorem></xml>"
    tei_json = json.loads(row[b'grobid0:tei_json'].decode('utf-8'))
    metadata = json.loads(row[b'grobid0:metadata'].decode('utf-8'))

def test_parse_cdx_invalid(job):

    print("valid")
    raw = io.BytesIO(b"com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 200 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz")
    info, status = job.parse_line(raw)
    assert status is None

    print("space-prefixed line")
    raw = io.BytesIO(b" com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 200 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz")
    info, status = job.parse_line(raw)
    assert info is None
    assert status['status'] == "invalid"
    assert 'prefix' in status['reason']

    print("commented line")
    raw = io.BytesIO(b"#com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 200 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz")
    info, status = job.parse_line(raw)
    assert info is None
    assert status['status'] == "invalid"
    assert 'prefix' in status['reason']

    print("wrong column count")
    raw = io.BytesIO(b"a b c d")
    info, status = job.parse_line(raw)
    assert info is None
    assert status['status'] == "invalid"
    assert 'parse' in status['reason']

    print("missing mimetype")
    raw = io.BytesIO(b"com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 200 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz")
    info, status = job.parse_line(raw)
    assert info is None
    assert status['status'] == "invalid"
    assert 'parse' in status['reason']

    print("HTTP status")
    raw = io.BytesIO(b"com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 501 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz")
    info, status = job.parse_line(raw)
    assert info is None
    assert status['status'] == "invalid"

    print("datetime")
    raw = io.BytesIO(b"com,sagepub,cep)/content/28/9/960.full.pdf 20170705 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 501 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz")
    info, status = job.parse_line(raw)
    assert info is None
    assert status['status'] == "invalid"


def test_parse_cdx_skip(job):

    print("warc format")
    raw = io.BytesIO(b"com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 200 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz")
    info, status = job.mapper(raw)
    assert info is None
    assert status['status'] == "skip"
    assert 'WARC' in status['reason']

    print("mimetype")
    raw = io.BytesIO(b"com,sagepub,cep)/content/28/9/960.full.pdf 20170705 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 200 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz")
    info, status = job.mapper(raw)
    assert info is None
    assert status['status'] == "skip"
    assert 'mimetype' in status['reason']

def test_tei_json_convert():
    # TODO: load xml test vector, run it through
    with open('tests/files/23b29ea36382680716be08fc71aa81bd226e8a85.xml', 'r') as f:
        xml_content = f.read()
    pass

def test_tei_json_convert_invalid():
    # TODO: pass in junk
    pass
