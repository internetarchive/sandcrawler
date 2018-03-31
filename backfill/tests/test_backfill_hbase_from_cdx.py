
import io
import json
import pytest
import mrjob
import happybase_mock
from backfill_hbase_from_cdx import MRCDXBackfillHBase

@pytest.fixture
def job():
    conn = happybase_mock.Connection()
    conn.create_table('wbgrp-journal-extract-test', {'file': {}, 'grobid0': {}})
    table = conn.table('wbgrp-journal-extract-test')

    job = MRCDXBackfillHBase(['--no-conf', '-'], hb_table=table)
    job.hb_table = table
    return job

#Example to read back rows...
"""
def basic_job_run_capturing_output(job):

    job.sandbox(stdin=open('tests/files/example.cdx', 'r'))
    results = []
    with job.make_runner() as runner:
        runner.run()
        for key, value in job.parse_output(runner.cat_output()):
            results.append(value)

    print(results)
    assert len(list(job.hb_table.scan())) == 5
"""

def test_some_lines(job):

    raw = io.BytesIO(b"""
com,sagepub,cep)/content/28/9/960.full.pdf 20170705062200 http://cep.sagepub.com/content/28/9/960.full.pdf application/pdf 301 3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ - - 401 313356621 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz
eu,eui,cadmus)/bitstream/handle/1814/36635/rscas_2015_03.pdf;jsessionid=761393014319a39f40d32ae3eb3a853f?sequence=1 20170705062202 http://cadmus.eui.eu/bitstream/handle/1814/36635/RSCAS_2015_03.pdf%3Bjsessionid%3D761393014319A39F40D32AE3EB3A853F?sequence%3D1 application/PDF 200 MPCXVWMUTRUGFP36SLPHKDLY6NGU4S3J - - 854156 328850624 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz
com,pbworks,educ333b)/robots.txt 20170705063311 http://educ333b.pbworks.com/robots.txt text/plain 200 6VAUYENMOU2SK2OWNRPDD6WTQTECGZAD - - 638 398190140 CITESEERX-CRAWL-2017-06-20-20170705062707827-00049-00058-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705063158203-00053-31209~wbgrp-svc284.us.archive.org~8443.warc.gz
""")

    job.sandbox(stdin=raw)
    job.run_mapper()

    assert job.hb_table.row(b'1') == {}
    # HTTP 301
    assert job.hb_table.row(b'3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ') == {}
    # valid
    assert job.hb_table.row(b'MPCXVWMUTRUGFP36SLPHKDLY6NGU4S3J') != {}
    # text/plain
    assert job.hb_table.row(b'6VAUYENMOU2SK2OWNRPDD6WTQTECGZAD') == {}

    row = job.hb_table.row(b'MPCXVWMUTRUGFP36SLPHKDLY6NGU4S3J')
    assert row[b'file:mime'] == b"application/pdf"
    json.loads(row[b'file:cdx'].decode('utf-8'))
