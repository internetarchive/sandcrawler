#!/usr/bin/env python3

import sys
import json

def grobid_ok(obj):
    return True

def run():
    for line in sys.stdin:
        obj = json.loads(line)
        if grobid_ok(obj):
            print(line.strip())

if __name__=="__main__":
    run()
