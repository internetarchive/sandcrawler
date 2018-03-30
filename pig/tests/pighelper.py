"""
A helper class for locally testing Pig scripts.

author: Bryan Newbold <bnewbold@archive.org>
"""
import os
import tempfile
import unittest
import subprocess
from nose.tools import *


class PigTestHelper(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls._pigpath= "./deps/pig/bin/pig"
        cls._base = [cls._pigpath,
            '-x', 'local',
            '-log4jconf', 'pig_log4j.properties',
            '-stop_on_failure']

        # Check that pig is functioning
        if subprocess.call(cls._base + ['-version']) != 0:
            raise unittest.SkipTest("Failed to find and run Pig")

        # Classpath?
        # os.path.join("pig-0.12.0-cdh5.0.1", "pig.jar"),
        # os.path.join("pig-0.12.0-cdh5.0.1", "lib", "*"),
        # "hadoop-2.3.0-cdh5.0.1"

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        os.rmdir(self._tmpdir)

    def run_pig_raw(self, params):
        """Low-level variant with params appended directly. Returns
        CompletedProcess, raises an error if return value isn't succes"""

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

