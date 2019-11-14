#!/usr/bin/env python3

"""
    input like:

        doi,ident,"release_stage"
        "10.7554/elife.38904",mxj534diw5gatc26rkif3io5xm,published
        "10.7554/elife.41855",kag74qc6dfex7ftpfkf7iaus44,published
        "10.7554/elife.41156",ienee5vxcbbbfhs2q54h4455hu,published
        "10.7554/elife.43230",52rpllol2rcndjqs3xfwcldeka,published
        "10.7554/elife.42591",fpz642gihrc3jd2vibg6gnjrxm,published

    output like:

    {
      "base_url": "https://doi.org/10.7554/elife.38904",
      "ext_ids": {
        "doi": "10.7554/elife.38904"
      },
      "fatcat_release": "mxj534diw5gatc26rkif3io5xm",
      "release_stage": "published"
    }
"""

import csv, sys, json

reader = csv.DictReader(sys.stdin)
for row in reader:
    d = {
      "base_url": "https://doi.org/{}".format(row['doi']),
      "ext_ids": {
        "doi": row['doi'],
      },
      "fatcat_release": row['ident'],
      "release_stage": row['release_stage'],
    }
    print(json.dumps(d))
