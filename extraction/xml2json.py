
import json
import sys
import xmltodict

with open('tests/files/23b29ea36382680716be08fc71aa81bd226e8a85.xml', 'rb') as f:
    thing = xmltodict.parse(f, process_namespaces=False)
    print(json.dumps(thing))
