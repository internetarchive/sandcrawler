
"""
Abstract into a base test class/template:

1. Needs deps downloaded and installed and env configured (bash? .env? makefile?)
2. In test, create tempdir for output. Print helpful info on every run
3. Run pig locally, inspect output files
"""

import os
import unittest
from nose.tools import *
from pigpy.hadoop import Hadoop


class TestFilterCDX(unittest.TestCase):

    def setUp(self):

        classpaths = [
            os.path.join("pig-0.12.0-cdh5.0.1", "pig.jar"),
            os.path.join("pig-0.12.0-cdh5.0.1", "lib", "*"),
        ]

        local_home = os.path.join("hadoop-2.3.0-cdh5.0.1")

        name_node = "file:///test/files"

        self.hadoop = Hadoop(local_home, name_node, classpaths)

    def test_thing(self):

        self.hadoop.run_pig_job("filter-cdx-ps.pig")
        self.hadoop.copyToLocal("/reports/output.csv", "output.csv")

