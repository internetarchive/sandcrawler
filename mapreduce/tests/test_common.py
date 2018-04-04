
from common import *


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

    assert parse_cdx_line(raw) == correct
    assert parse_cdx_line(raw + "\n") == correct
    assert parse_cdx_line(raw + " extra_field") == correct
