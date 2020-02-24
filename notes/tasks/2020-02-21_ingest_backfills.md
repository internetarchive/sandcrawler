
Follow-ups to last ingest backfill. Only run these when ingest request topic is
empty, and full persist chain has run successfully.

## Corona virus stuff

    ./fatcat_ingest.py --limit 2000 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --allow-non-oa query coronavirus

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --allow-non-oa query 2019-nCoV

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --allow-non-oa query MERS-CoV

## Large OA Publishers

Should probably check domain stats/success for all of these first.

Would also be good to have a "randomize" option. Could fake that by dumping to
disk first.

    ./fatcat_ingest.py --limit 2000 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --after-year 2020 container --publisher elsevier

    ./fatcat_ingest.py --dry-run --limit 500 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --after-year 2020 container --publisher springer

    # ???
    ./fatcat_ingest.py --limit 1000 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --allow-non-oa container --container-id zpobyv4vbranllc7oob56tgci4

## Fixed OA Publishers (small tests)

    # american archivist
    ./fatcat_ingest.py --limit 25 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --allow-non-oa container --container-id zpobyv4vbranllc7oob56tgci4
    => Expecting 2920 release objects in search queries
    => Counter({'estimate': 2920, 'elasticsearch_release': 26, 'ingest_request': 25, 'kafka': 25})
    => good

    ./fatcat_ingest.py --limit 25 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org container --publisher Gruyter
    => Expecting 42897 release objects in search queries
    => Counter({'estimate': 42897, 'ingest_request': 25, 'kafka': 25, 'elasticsearch_release': 25})

    ./fatcat_ingest.py --limit 25 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org container --publisher frontiers
    => Expecting 35427 release objects in search queries
    => Counter({'estimate': 35427, 'kafka': 25, 'elasticsearch_release': 25, 'ingest_request': 25})
    => mixed results?

    ./fatcat_ingest.py --limit 25 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org container --publisher mdpi
    => Expecting 43111 release objects in search queries
    => Counter({'estimate': 43111, 'elasticsearch_release': 25, 'ingest_request': 25, 'kafka': 25})
    => success, fast

    ./fatcat_ingest.py --limit 25 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org container --publisher "American Heart Association"
    => Expecting 185240 release objects in search queries
    => Counter({'estimate': 185240, 'kafka': 25, 'ingest_request': 25, 'elasticsearch_release': 25})
    => no success? or mixed? skip for now

    # Environmental Health Perspectives (NIH)
    ./fatcat_ingest.py --limit 25 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org container --container-id 3w6amv3ecja7fa3ext35ndpiky
    => ["no-pdf-link",null,"https://ehp.niehs.nih.gov/doi/10.1289/ehp.113-a51"]
    => ["no-pdf-link",null,"https://ehp.niehs.nih.gov/doi/10.1289/ehp.113-a51"]
    => FIXED
    => good (but slow?)

    ./fatcat_ingest.py --limit 50 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org container --publisher "Tomsk State University"
    => Expecting 578057 release objects in search queries
    => Counter({'estimate': 578057, 'elasticsearch_release': 50, 'kafka': 50, 'ingest_request': 50})
    => nothing from tsu.ru? skip for now

    ./fatcat_ingest.py --limit 25 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org container --name "cogent"
    => Expecting 4602 release objects in search queries
    => Counter({'estimate': 4602, 'kafka': 25, 'elasticsearch_release': 25, 'ingest_request': 25})
    => good

    ./fatcat_ingest.py --limit 25 --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org query "doi:10.26434\/chemrxiv*"
    => Expecting 5690 release objects in search queries
    => Counter({'estimate': 5690, 'ingest_request': 25, 'kafka': 25, 'elasticsearch_release': 25})
    => good


## Fixed OA Publishers (full runs)

    # american archivist
    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org --allow-non-oa container --container-id zpobyv4vbranllc7oob56tgci4
    Expecting 2920 release objects in search queries
    Counter({'estimate': 2920, 'elasticsearch_release': 2920, 'kafka': 2911, 'ingest_request': 2911})

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org container --publisher Gruyter
    Expecting 42986 release objects in search queries
    Counter({'estimate': 42986, 'elasticsearch_release': 42986, 'kafka': 42935, 'ingest_request': 42935})

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org container --publisher mdpi
    Expecting 43108 release objects in search queries
    Counter({'estimate': 43108, 'elasticsearch_release': 43108, 'ingest_request': 41262, 'kafka': 41262})

    # Environmental Health Perspectives (NIH)
    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org container --container-id 3w6amv3ecja7fa3ext35ndpiky
    Expecting 12699 release objects in search queries
    Counter({'elasticsearch_release': 12699, 'estimate': 12699, 'kafka': 12615, 'ingest_request': 12615})

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org container --name "cogent"
    Expecting 4602 release objects in search queries
    Counter({'estimate': 4602, 'ingest_request': 4602, 'kafka': 4602, 'elasticsearch_release': 4602})

    ./fatcat_ingest.py --env prod --enqueue-kafka --kafka-hosts wbgrp-svc263.us.archive.org query "doi:10.26434\/chemrxiv*"
    Expecting 5690 release objects in search queries
    Counter({'ingest_request': 5690, 'kafka': 5690, 'estimate': 5690, 'elasticsearch_release': 5690})

