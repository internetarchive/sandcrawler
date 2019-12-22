
import os
import unittest
from pighelper import PigTestHelper, count_lines


class TestFilterCDXPaperPdfs(PigTestHelper):

    def test_papers_domain_words(self):
        r = self.run_pig("filter-cdx-paper-pdfs.pig", "tests/files/papers_domain_words.cdx")
        assert count_lines(r) == 4

    def test_papers_edu_tilde(self):
        r = self.run_pig("filter-cdx-paper-pdfs.pig", "tests/files/papers_edu_tilde.cdx")
        assert count_lines(r) == 6

    def test_papers_url_doi(self):
        r = self.run_pig("filter-cdx-paper-pdfs.pig", "tests/files/papers_url_doi.cdx")
        assert count_lines(r) == 2

    def test_papers_url_words(self):
        r = self.run_pig("filter-cdx-paper-pdfs.pig", "tests/files/papers_url_words.cdx")
        assert count_lines(r) == 12

