
import pytest

from sandcrawler.xml import xml_reserialize


def test_xml_reserialize() -> None:
    
    with open('tests/files/scielo_article.jats.xml', 'rb') as f:
        raw_xml = f.read()

    assert b'encoding="ISO-8859-1"' in raw_xml
    raw_xml.decode("ISO-8859-1")
    with pytest.raises(UnicodeDecodeError):
        raw_xml.decode("utf-8")

    str_xml = xml_reserialize(raw_xml)
    assert 'encoding="UTF-8"' in str_xml
