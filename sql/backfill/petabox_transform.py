#!/usr/bin/env python3

import json, sys, os

for l in sys.stdin.readlines():
    l = l.strip()
    if not l:
        continue
    r = json.loads(l)
    if not r['sha1']:
        continue
    sha1hex = r['sha1']
    for url in r['urls']:
        u = url['url']
        if not '//archive.org/' in u:
            continue
        u = u.split('/')
        if u[2] == 'web.archive.org':
            continue
        #print(u)
        assert u[2] == 'archive.org' and u[3] in ('download', 'serve')
        item = u[4]
        path = '/'.join(u[5:])
        print("\t".join([item, path, sha1hex]))
