#!/usr/bin/env python3
"""
Quick CLI script to convert a PDF to thumbnail (.png, jpeg, etc).

Originally used to benchmark and compare file size/quality.
"""

import sys

import poppler
from PIL import Image


def run(inpath, outpath):

    try:
        pdf = poppler.load_from_file(inpath)
        page = pdf.create_page(0)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(0)

    renderer = poppler.PageRenderer()
    full_page = renderer.render_page(page)
    img = Image.frombuffer("RGBA", (full_page.width, full_page.height), full_page.data, 'raw',
                           "BGRA", 0, 1)
    img.thumbnail((180, 300), Image.BICUBIC)
    #img.thumbnail((360,600), Image.BICUBIC)
    img.save(outpath)
    #img.save(outpath, quality=95)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("expect two parameters: INPUT.png OUTPUT.png", file=sys.stderr)
        sys.exit(-1)
    run(sys.argv[1], sys.argv[2])
