
import os
import unittest
from pighelper import PigTestHelper

class TestFilterCDX(PigTestHelper):

    def test_thing(self):
        self.run_pig("filter-cdx-ps.pig", "tests/files/example.cdx")
