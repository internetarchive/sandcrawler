
### QA matchcrossref

[D8C7F2CA7620450991838D540489948D/8B17786779BE44579C98D8A325AC5959] sandcrawler.ScoreJob/(1/1) ...-24-2102.32-matchcrossref

Submitted:  Fri Aug 24 21:03:09 UTC 2018
Started:    Fri Aug 24 21:03:20 UTC 2018
Finished:   Sat Aug 25 09:46:55 UTC 2018
Elapsed:    12hrs, 43mins, 34sec
Diagnostics:    
Average Map Time    24mins, 31sec
Average Shuffle Time    15sec
Average Merge Time  21sec
Average Reduce Time 7mins, 17sec

Map 2312    2312
Reduce  100 100

crossref-rows-filtered  73901964    0   73901964
grobid-rows-filtered    1092992 0   1092992
joined-rows 0   623837  623837

cascading.flow.StepCounters 
Tuples_Read 94831255    0   94831255
Tuples_Written  0   623837  623837

Read_Duration   7108430 352241  7460671
Tuples_Read 94831255    74994956    169826211
Tuples_Written  74994956    623837  75618793
Write_Duration  7650302 21468   7671770

## QA UnGrobided

Submitted:  Sat Aug 25 01:23:22 UTC 2018
Started:    Sat Aug 25 05:06:36 UTC 2018
Finished:   Sat Aug 25 05:13:45 UTC 2018
Elapsed:    7mins, 8sec
Diagnostics:    
Average Map Time    1mins, 20sec
Average Shuffle Time    12sec
Average Merge Time  15sec
Average Reduce Time 29sec

Map 48  48
Reduce  1   1

bnewbold@bnewbold-dev$ gohdfs du -sh sandcrawler/output-qa/2018-08-25-0122.54-dumpungrobided/part*
56.8M   /user/bnewbold/sandcrawler/output-qa/2018-08-25-0122.54-dumpungrobided/part-00000

## Prod UnGrobided

[D76F6BF91D894E879E747C868B0DEDE7/394A1AFC44694992B71E6920AF8BA3FB] sandcrawler.DumpUnGrobidedJob/(1/1) ...26-0910.25-dumpungrobided

Map    278 278
Reduce  1   1

Submitted:  Sun Aug 26 09:10:51 UTC 2018
Started:    Sun Aug 26 09:18:21 UTC 2018
Finished:   Sun Aug 26 10:29:28 UTC 2018
Elapsed:    1hrs, 11mins, 7sec
Diagnostics:    
Average Map Time    4mins, 48sec
Average Shuffle Time    24mins, 17sec
Average Merge Time  14sec
Average Reduce Time 13mins, 54sec


cading.flow.StepCounters    
Name
Map
Reduce
Total
Tuples_Read 64510564    0   64510564
Tuples_Written  0   21618164    21618164

## Prod Crossref Match

[6C063C0809244446BA8602C3BE99CEC2/5FE5D87899154F38991A1ED58BEB34D4] sandcrawler.ScoreJob/(1/1) ...-25-1753.01-matchcrossref

Map 2427    2427
Reduce  50  50

Submitted:  Sat Aug 25 17:53:50 UTC 2018
Started:    Sat Aug 25 17:53:59 UTC 2018
Finished:   Sun Aug 26 11:22:52 UTC 2018
Elapsed:    17hrs, 28mins, 52sec
Diagnostics:    
Average Map Time    31mins, 20sec
Average Shuffle Time    1mins, 21sec
Average Merge Time  41sec
Average Reduce Time 3hrs, 14mins, 39sec

crossref-rows-filtered  73901964    0   73901964
grobid-rows-filtered    14222226    0   14222226
joined-rows 0   14115453    14115453

## "Prod" Fatcat Group Works (run 2019-08-10)

    ./please --prod groupworks-fatcat hdfs:///user/bnewbold/release_export.2019-07-07.json

    job_1559844455575_118299
    http://ia802401.us.archive.org:6988/proxy/application_1559844455575_118299

## Re-GROBID batch (2019-11-12)

Want to re-process "old" GROBID output with newer (0.5.5+fatcat) GROBID version
(vanilla training) plus biblio-glutton identification. Hoping to make a couple
million new fatcat matches; will probably do a later round of ML matching over
this batch as well.

    # in /grande/regrobid

    # as postgres
    psql sandcrawler < dump_regrobid_pdf.sql > dump_regrobid_pdf.txt

    # as bnewbold
    cat dump_regrobid_pdf.txt | sort -S 4G | uniq -w 40 | cut -f2 | pv -l > dump_regrobid_pdf.2019-11-12.json
    # 41.5M lines, uniq by SHA1
    # NOTE: not the full 56m+ from GROBID table... some in archive.org, others
    # not application/pdf type. Will need to follow-up on those later

    # intend to have 3 worker machines, but splitting 6 ways in case we need to
    # re-balance load or get extra machines or something
    split -n l/6 -a1 -d --additional-suffix=.json dump_regrobid_pdf.2019-11-12.json regrobid_cdx.split_

    # distribute to tmp001, tmp002, tmp003:
    tmp001: 0,1
    tmp002: 2,3
    tmp003: 4,5

    # test local grobid config:
    head /srv/sandcrawler/tasks/regrobid_cdx.split_0.json | pv -l | ./grobid_tool.py --grobid-host http://localhost:8070 -j0 extract-json - > example_out.json
    # expect at least a couple fatcat matches
    cat example_out.json | jq .tei_xml -r | rg fatcat

    # test GROBID+kafka config:
    cat /srv/sandcrawler/tasks/regrobid_cdx.split_*.json | pv -l | head | parallel -j40 --linebuffer --round-robin --pipe ./grobid_tool.py --kafka-env prod --kafka-hosts wbgrp-svc263.us.archive.org:9092,wbgrp-svc284.us.archive.org:9092,wbgrp-svc285.us.archive.org:9092 --kafka-mode --grobid-host http://localhost:8070 -j0 extract-json -
    
    # full run, in a screen session
    cat /srv/sandcrawler/tasks/regrobid_cdx.split_*.json | pv -l | parallel -j40 --linebuffer --round-robin --pipe ./grobid_tool.py --kafka-env prod --kafka-hosts wbgrp-svc263.us.archive.org:9092,wbgrp-svc284.us.archive.org:9092,wbgrp-svc285.us.archive.org:9092 --kafka-mode --grobid-host http://localhost:8070 -j0 extract-json -

NOTE: really should get parallel kafka worker going soon. if there is a reboot
or something in the middle of this process, will need to re-run from the start.

Was getting a bunch of weird kafka INVALID_MSG errors on produce. Would be nice to be able to retry, so doing:

    cat /srv/sandcrawler/tasks/regrobid_cdx.split_*.json | pv -l | parallel --joblog regrobid_job.log --retries 5 -j40 --linebuffer --pipe ./grobid_tool.py --kafka-env prod --kafka-hosts wbgrp-svc263.us.archive.org:9092,wbgrp-svc284.us.archive.org:9092,wbgrp-svc285.us.archive.org:9092 --kafka-mode --grobid-host http://localhost:8070 -j0 extract-json -

Never mind, going to split into chunks which can be retried.

    cd /srv/sandcrawler/tasks
    sudo chown sandcrawler:staff .
    cat regrobid_cdx.split_* | split -l 20000 -a4 -d --additional-suffix=.json - chunk_
    ls /srv/sandcrawler/tasks/chunk_*.json | parallel -j4 ./extract_chunk.sh {}

extract_chunk.sh:


    #!/bin/bash

    set -x -e -u -o pipefail

    if [ -f $1.SUCCESS ]; then
        echo "Skipping: $1..."
        exit
    fi

    echo "Extracting $1..."

    date
    cat $1 | parallel -j10 --linebuffer --round-robin --pipe ./grobid_tool.py --kafka-env prod --kafka-hosts wbgrp-svc263.us.archive.org:9092,wbgrp-svc284.us.archive.org:9092,wbgrp-svc285.us.archive.org:9092 --kafka-mode --grobid-host http://localhost:8070 -j0 extract-json -

    touch $1.SUCCESS

seems to be working better! tested and if there is a problem with one chunk the others continue

## Pig Joins (around 2019-12-24)

Partial (as a start):

    pig -param INPUT_CDX="/user/bnewbold/pdfs/gwb-pdf-20191005172329" -param INPUT_DIGEST="/user/bnewbold/scihash/shadow.20191222.sha1b32.sorted" -param OUTPUT="/user/bnewbold/scihash/gwb-pdf-20191005172329.shadow.20191222.join.cdx" join-cdx-sha1.pig

    HadoopVersion   PigVersion      UserId  StartedAt       FinishedAt      Features
2.6.0-cdh5.11.2 0.12.0-cdh5.0.1 bnewbold        2019-12-27 00:39:38     2019-12-27 15:32:44     HASH_JOIN,ORDER_BY,DISTINCT,FILTER

    Success!

    Job Stats (time in seconds):
    JobId   Maps    Reduces MaxMapTime      MinMapTIme      AvgMapTime      MedianMapTime   MaxReduceTime   MinReduceTime   AvgReduceTime   MedianReducetime      Alias   Feature Outputs
    job_1574819148370_46540 4880    0       143     10      27      21      n/a     n/a     n/a     n/a     cdx     MAP_ONLY
    job_1574819148370_46541 19      0       59      9       25      18      n/a     n/a     n/a     n/a     digests MAP_ONLY
    job_1574819148370_46773 24      1       17      7       10      9       6       6       6       6       digests SAMPLER
    job_1574819148370_46774 7306    1       55      4       7       7       25      25      25      25      cdx     SAMPLER
    job_1574819148370_46778 7306    40      127     8       18      15      4970    1936    2768    2377    cdx     ORDER_BY
    job_1574819148370_46779 24      20      80      24      60      66      90      26      38      37      digests ORDER_BY
    job_1574819148370_46822 22      3       101     27      53      48      1501    166     735     539             DISTINCT
    job_1574819148370_46828 7146    959     122     7       16      14      91      21      35      32      full_join,result        HASH_JOIN    /user/bnewbold/scihash/gwb-pdf-20191005172329.shadow.20191222.join.cdx,

    Input(s):
    Successfully read 1968654006 records (654323590996 bytes) from: "/user/bnewbold/pdfs/gwb-pdf-20191005172329"
    Successfully read 74254196 records (2451575849 bytes) from: "/user/bnewbold/scihash/shadow.20191222.sha1b32.sorted"

    Output(s):
    Successfully stored 0 records in: "/user/bnewbold/scihash/gwb-pdf-20191005172329.shadow.20191222.join.cdx"

Oops! Didn't upper-case the sha1b32 output.

Full GWB:

    pig -param INPUT_CDX="/user/bnewbold/pdfs/gwb-pdf-20191005172329" -param INPUT_DIGEST="/user/bnewbold/scihash/shadow.20191222.sha1b32.sorted" -param OUTPUT="/user/bnewbold/scihash/gwb-pdf-20191005172329.shadow.20191222.join.cdx" join-cdx-sha1.pig
