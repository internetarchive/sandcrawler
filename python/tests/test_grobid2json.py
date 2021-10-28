import json
import xml

import pytest
from grobid_tei_xml import parse_document_xml


def test_small_xml():
    """
    This used to be a test of grobid2json; now it is a compatability test for
    the to_legacy_dict() feature of grobid_tei_xml.
    """

    with open("tests/files/small.xml", "r") as f:
        tei_xml = f.read()
    with open("tests/files/small.json", "r") as f:
        json_form = json.loads(f.read())

    tei_doc = parse_document_xml(tei_xml)
    assert tei_doc.to_legacy_dict() == json_form


def test_invalid_xml():

    with pytest.raises(xml.etree.ElementTree.ParseError):
        parse_document_xml("this is not XML")
    with pytest.raises(ValueError):
        parse_document_xml("<xml></xml>")
