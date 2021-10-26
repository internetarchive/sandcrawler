import xml.etree.ElementTree as ET


def xml_reserialize(raw: bytes) -> str:
    root = ET.fromstring(raw)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
