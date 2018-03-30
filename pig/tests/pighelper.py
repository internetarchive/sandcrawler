"""
A helper class for locally testing Pig scripts.

Include `PigTestHelper` and extend in your test classes, call `self.run_pig()`
with your script and example input file, then look at the output (at returned
path) to check for validity.

TODO: squelch pig stdout going to console, presumably because of subprocess.run
behavior

author: Bryan Newbold <bnewbold@archive.org>
"""
import os
import shutil
import tempfile
import unittest
import subprocess
from nose.tools import *


class PigTestHelper(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls._pigpath= "./deps/pig/bin/pig"
        cls._classpath = "./deps/hadoop/share/hadoop/common/lib"
        cls._base = [cls._pigpath,
            '-x', 'local',
            '-P', './tests/pig.properties']

        # Check that pig is functioning
        if subprocess.call(cls._base + ['-version']) != 0:
            raise unittest.SkipTest("Failed to find and run Pig")

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self._tmpdir)

    def run_pig_raw(self, params):
        """Low-level variant with params appended directly. Returns
        CompletedProcess, raises an error if return value isn't succes"""

        print("Running: {}".format(' '.join(self._base + params)))
        retval = subprocess.run(self._base + params,
            timeout=20.0,
            check=True)
        return retval

    def run_pig(self, script_path, in_file, **kwargs):
        """Convenience helper around run_pig().
        
        INPUT parameter is set to in_file.
        OUTPUT parameter is set to a random file.
        Any keyword args are passed as parameters.
        """

        pargs = []
        for key, value in kwargs.items():
            pargs.append('-p')
            pargs.append('{}={}'.format(key, value))

        out_file = tempfile.mktemp(dir=self._tmpdir)
        params = [
            '-f', script_path,
            '-p', 'INPUT={}'.format(in_file),
            '-p', 'OUTPUT={}'.format(out_file),
            ] + pargs
        self.run_pig_raw(params)
        return out_file

    # TODO: helper to verify that output matches an expected file
