#!/usr/bin/env python3
"""
Takes an "joined" TSV input stream:

- sha1
- dois (JSON list)
- cdx (JSON object)
    - url
    - dt
    (etc)
- mimetype
- size (integer)

And outputs JSON objects that are can be imported into fatcat with the
"matched" script.

No dependencies (only python3 stdlib)
"""

import sys
import json
import base64

def run():
    for line in sys.stdin:
        line = line.split('\t')
        assert len(line) == 5
        raw_sha1 = line[0].replace('sha1:', '')
        dois = json.loads(line[1])
        cdx = json.loads(line[2])
        mimetype = line[3]
        size = int(line[4])

        sha1 = base64.b16encode(base64.b32decode(raw_sha1)).decode('ascii').lower()

        obj = dict(
            sha1=sha1,
            dois=dois,
            cdx=[dict(url=cdx['url'], dt=cdx['dt'])],
            size=size,
            mimetype=mimetype)
        print(json.dumps(obj))

if __name__=='__main__':
    run()
