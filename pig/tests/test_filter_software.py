
import os
import unittest
from pighelper import PigTestHelper

def count_lines(s):
    return len([l for l in s.strip().split('\n') if len(l) > 0])

class TestFilterCDXSoftware(PigTestHelper):

    def test_tarballs(self):
        r = self.run_pig("filter-cdx-tarball.pig", "tests/files/tarballs.cdx")
        assert count_lines(r) == 2

    def test_source_code(self):
        r = self.run_pig("filter-cdx-source-code-crude.pig", "tests/files/sourcecode.cdx")
        assert count_lines(r) == 1

