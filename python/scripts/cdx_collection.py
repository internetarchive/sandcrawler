#!/usr/bin/env python3
"""
Fetches and merges all CDX files for a collection.

Calls metadata API to enumerate all items/files, then fetches and concatanates
them all. Requires the 'internetarchive' library.

Call with a collection name:

    ./cdx_collection SOME_COLLECTION_NAME
"""

import os
import shutil
import subprocess
import sys
import tempfile

import internetarchive as ia
import requests


def run():

    if len(sys.argv) != 2:
        print("Expected a single argument (collection name)")
        sys.exit(-1)

    collection = sys.argv[1]

    # Check collection name is clean
    assert collection.replace("_", "").replace("-", "").replace(".", "").isalnum()

    tempdir = tempfile.mkdtemp()
    print("Looking up collection: {}".format(collection))

    # First fetch list
    item_list = list(ia.search_items(query="collection:{} mediatype:web".format(collection)))

    if len(item_list) == 0:
        print("No items found, bailing")
        sys.exit(-1)

    print("Found {} potential items".format(len(item_list)))
    status = True
    errors = []
    for item in item_list:
        item = item["identifier"]
        # TODO: error handling
        try:
            ret = ia.download(
                item,
                files=[item + ".cdx.gz"],
                verbose=True,
                destdir=tempdir,
                no_directory=True,
                retries=1000,
            )
            status = ret and status
        except requests.exceptions.ReadTimeout as rt:
            print(str(rt), file=sys.stderr)
            errors.append(rt)
            continue

    if errors:
        print("## Download Errors", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)

    # Combine files
    print("Merging and re-compressing all CDX files...")
    # subprocess.run('zcat {0}/*.cdx.gz | pigz > {0}/combined.gz'.format(tempdir),
    subprocess.run("zcat {0}/*.cdx.gz | gzip > {0}/combined.gz".format(tempdir), shell=True)

    # Move and cleanup
    shutil.move("{}/combined.gz".format(tempdir), "{}.cdx.gz".format(collection))

    print("Done!")


if __name__ == "__main__":
    run()
