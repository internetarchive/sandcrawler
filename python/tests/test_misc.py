
import pytest

from sandcrawler import gen_file_metadata, b32_hex, parse_cdx_line

def test_gen_file_metadata():
    
    # valid (but very small) PDF file
    with open('tests/files/dummy.pdf', 'rb') as f:
        file_meta = gen_file_metadata(f.read())
    assert file_meta == {
        'mimetype': 'application/pdf',
        'md5hex': '2942bfabb3d05332b66eb128e0842cff',
        'sha1hex': '90ffd2359008d82298821d16b21778c5c39aec36',
        'sha256hex': '3df79d34abbca99308e79cb94461c1893582604d68329a41fd4bec1885e6adb4',
        'size_bytes': 13264,
    }

    # valid HTML
    fm = gen_file_metadata(
        b"""<html><head><title>dummy</title></head><body>html document</body></html>""")
    assert fm['mimetype'] == 'text/html'

    # bogus text
    fm = gen_file_metadata(b"asdf1234")
    assert fm['mimetype'] == 'text/plain'
    assert fm['size_bytes'] == 8

def test_b32_hex():

    # valid b32
    assert b32_hex('sha1:TZCYZ2ULEHYGESS4L3RNH75I23KKFSMC') == '9e458cea8b21f0624a5c5ee2d3ffa8d6d4a2c982'
    assert b32_hex('TZCYZ2ULEHYGESS4L3RNH75I23KKFSMC') == '9e458cea8b21f0624a5c5ee2d3ffa8d6d4a2c982'

    # sha1hex pass-through
    s = 'bda3c1017d52e826bbd1da51efad877272d300f9'
    assert b32_hex(s) == s

    # invalid
    with pytest.raises(ValueError):
        assert b32_hex('blah') == 'blah'

def test_parse_cdx_line():

    raw = "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz"
    correct = {
        'sha1b32': "WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G",
        'sha1hex': "b2f65203da9929c2f758e8dd587b5524f904dbe6",
        'mimetype': "application/pdf",
        'surt': "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf",
        'url': "https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf",
        'datetime': "20170828233154",
        'warc_path': "SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz",
        'warc_offset': 931661233,
        'warc_csize': 210251,
        'http_status': 200,
    }

    assert parse_cdx_line(raw) == correct
    assert parse_cdx_line(raw + "\n") == correct
    assert parse_cdx_line(raw + " extra_field") == correct

def test_invalid_cdx():

    print("missing warc")
    raw = "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 -"
    assert parse_cdx_line(raw) == None

    print("bad datetime")
    raw = "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 2070828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233i SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz" 
    assert parse_cdx_line(raw) == None
