
import json
import pytest
from grobid2json import *


def test_small_xml():
    
    with open('tests/files/small.xml', 'r') as f:
        tei_xml = f.read()
    with open('tests/files/small.json', 'r') as f:
        json_form  = json.loads(f.read())

    assert teixml2json(tei_xml) == json_form
