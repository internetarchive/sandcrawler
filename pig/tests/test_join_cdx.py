
import os
import unittest
import tempfile
import subprocess
from pighelper import PigTestHelper, count_lines

class TestJoinCDXSha1(PigTestHelper):

    def run_pig_join(self, script_path, cdx_file, digest_file, **kwargs):
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
            '-p', 'INPUT_CDX={}'.format(cdx_file),
            '-p', 'INPUT_DIGEST={}'.format(digest_file),
            '-p', 'OUTPUT={}'.format(out_file),
            ] + pargs
        status = self.run_pig_raw(params)
        assert status.returncode == 0
        # Capture all the part-r-* files
        print("out_file: {}".format(out_file))
        subprocess.run("/bin/ls -la {}/part-*".format(out_file), shell=True)
        sub = subprocess.run("/bin/cat {}/part-*".format(out_file), stdout=subprocess.PIPE, shell=True)
        out = sub.stdout.decode('utf-8')
        print(out)
        return out

    # TODO: helper to verify that output matches an expected file

    def test_thing(self):
        r = self.run_pig_join("join-cdx-sha1.pig", "tests/files/example.cdx", "tests/files/example.sha1b32")
        assert count_lines(r) == 4
