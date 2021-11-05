
The current sandcrawler-db crossref table was backfilled from a 2021-01
snapshot, and has not been updated since.

Would like to use the existing fatcat Kafka feed to keep the crossref table up
to date, and also backfill in GROBID reference parsing of all `unstructured`
references.

Current plan is:

1. use kafkacat CLI to dump crossref Kafka topic, from the begining of 2021 up
   to some recent date
2. use `persist_tool.py`, with a large batch size (200?) to backfill this dump
   into sandcrawler-db. this will update some rows multiple times (if there
   have been updates)
3. dump the full crossref table, as a point-in-time snapshot
4. filter to crossref records that have `unstrutured` references in them (at
   all)
5. use `grobid_tool.py` with `parallel` to batch process references
6. backfill these refs using a simple SQL COPY statement
7. deploy crossref persist worker, with ref updates on, and roll the consumer
   group back to date of dump
8. wait for everything to catch up


## Commands

Get a timestamp in milliseconds:

    2021-01-01 is:
        1609488000 in unix time (seconds)
        1609488000000 in miliseconds

Hrm, oldest messages seem to actually be from 2021-04-28T19:21:10Z though. Due
to topic compaction? Yup, we have a 180 day compaction policy on that topic,
probably from when kafka space was tight. Oh well!

Updated retention for this topic to `46656000000` (~540 days, ~18 months) using
`kafka-manager` web app.

    kafkacat -C -b wbgrp-svc263.us.archive.org -t fatcat-prod.api-crossref -o s@1609488000000 \
        | pv -l \
        | gzip \
        > crossref_feed_start20210428_end20211029.json.gz

This resulted in ~36 million rows, 46GB.

`scp` that around, then run persist on `sandcrawler-db`:

    # in pipenv, as sandcrawler user
    # manually edited to set batch size to 200
    zcat /srv/sandcrawler/tasks/crossref_feed_start20210428_end20211029.json.gz \
        | pv -l \
        | ./persist_tool.py crossref -
    => 36.8M 11:02:43 [ 925 /s]

With a single thread, the persist process runs at about 1,000 rows/sec, which
works out to about 10 hours for 36 million rows.

At the start of this process, total PostgreSQL database size is 832.21G. At the
end, 902.51G. Have not run a `VACUUM ALL` or anything like that.

Query to dump crossref rows which have any refs and compress output with pigz:

    # dump_crossref.sql
    COPY (
        SELECT record
        FROM crossref
        WHERE record::jsonb @? '$.reference[*].unstructured'
        -- LIMIT 5
    )
    TO STDOUT
    WITH NULL '';

    # 'sed' required because of double quote escaping in postgresql output::
    # https://stackoverflow.com/questions/29869983/postgres-row-to-json-produces-invalid-json-with-double-escaped-quotes/29871069
    # 'rg' filter is just being conservative

    # XXX: next time add to the pipeline: rg -v "\\\\"
    # or, find some way to filter/transform this kind of SQL export better?
    psql sandcrawler < dump_crossref.sql \
        | sed 's/\\"/\"/g' \
        | rg '^\{' \
        | pv -l \
        | pigz \
        > /srv/sandcrawler/tasks/crossref_sandcrawler_unstructured.json.gz
    => 26.1M 3:22:51 [2.15k/s]

    # NOTE: -j40 is for production run with ~dedicated GROBID server with many cores
    zcat /srv/sandcrawler/tasks/crossref_sandcrawler_unstructured.json.gz \
        | rg -v "\\\\" \
        | parallel -j35 --linebuffer --round-robin --pipe ./grobid_tool.py --grobid-host http://wbgrp-svc096.us.archive.org:8070 parse-crossref-refs - \
        | pv -l \
        | pigz \
        > /srv/sandcrawler/tasks/crossref_sandcrawler_unstructured.grobid_refs.json.gz

    # from earlier testing with -j40: able to do about 300-500 records/second
    # 23.9k 0:01:14 [ 320 /s]
    # 134518 total refs parsed
    # ~1817 refs/second parsed

    # with errors, got through about: 2.08M 1:38:20 [ 352 /s]
    # was still seing bad JSON?
    # JSON lines pushed: Counter({'total': 105898, 'pushed': 105886, 'error-json-decode': 12})

    # finally, without errors:
    # 18.6M 8:35:02 [ 603 /s]

In the next step, going to need a small direct persist worker to copy lines
verbatim into just the `grobid_refs` table.

## Errors

Got errors when running for real:

    xml.etree.ElementTree.ParseError: not well-formed (invalid token): line 114, column 33

    requests.exceptions.HTTPError: 500 Server Error: Internal Server Error for url: http://wbgrp-svc096.us.archive.org:8070/api/processCitationList

    urllib3.exceptions.MaxRetryError: HTTPConnectionPool(host='wbgrp-svc096.us.archive.org', port=8070): Max retries exceeded with url: /api/processCitationList (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f54b0a3bd00>: Failed to establish a new connection: [Errno 99] Cannot assign requested address'))


    Nov 03 06:57:32 wbgrp-svc096.us.archive.org GROBID[400404]: ERROR [2021-11-03 06:57:32,569] org.grobid.service.process.GrobidRestProcessString: An unexpected exception occurs.
    Nov 03 06:57:32 wbgrp-svc096.us.archive.org GROBID[400404]: ! java.lang.NullPointerException: null
    Nov 03 06:57:32 wbgrp-svc096.us.archive.org GROBID[400404]: ! at org.grobid.core.data.BiblioItem.cleanTitles(BiblioItem.java:1784)
    Nov 03 06:57:32 wbgrp-svc096.us.archive.org GROBID[400404]: ! at org.grobid.core.engines.CitationParser.processingLayoutTokenMultiple(CitationParser.java:175)
    Nov 03 06:57:32 wbgrp-svc096.us.archive.org GROBID[400404]: ! at org.grobid.core.engines.CitationParser.processingStringMultiple(CitationParser.java:92)
    Nov 03 06:57:32 wbgrp-svc096.us.archive.org GROBID[400404]: ! at org.grobid.core.engines.Engine.processRawReferences(Engine.java:168)
    Nov 03 06:57:32 wbgrp-svc096.us.archive.org GROBID[400404]: ! at org.grobid.service.process.GrobidRestProcessString.processCitationList(GrobidRestProcessString.java:316)
    Nov 03 06:57:32 wbgrp-svc096.us.archive.org GROBID[400404]: ! at org.grobid.service.GrobidRestService.processCitationListReturnXml_post(GrobidRestService.java:581)
    Nov 03 06:57:32 wbgrp-svc096.us.archive.org GROBID[400404]: ! at sun.reflect.GeneratedMethodAccessor19.invoke(Unknown Source)
    Nov 03 06:57:32 wbgrp-svc096.us.archive.org GROBID[400404]: ! at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
    Nov 03 06:57:32 wbgrp-svc096.us.archive.org GROBID[400404]: ! at java.lang.reflect.Method.invoke(Method.java:498)
    [...]

Bogus example reference causing 500 error (among other non-error citations) (doi:10.5817/cz.muni.m210-9541-2019):

    'Müller, R., Šidák, P. (2012). Slovník novější literární teorie. Praha: Academia.'
    '\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0'
    'Šotkovská, J. (2008). Rané divadelní hry Milana Uhdeho; diplomová práce. Brno: Masarykova univerzita.',

s.strip() in python would remove these non-breaking spaces (update: implemented this later)

    Maheswari, S., Vijayalakshmi, C.: Optimization Model for Electricity Distribution System Control using Communication System by La-grangian Relaxation Technique. CiiT International Journal of Wireless Communication 3(3), 183–187 (2011) (Print: ISSN 0974 – 9756 & Online: ISSN 0974 – 9640)

Also:

    truncating very large reference list for doi:10.1017/chol9780521264303.033 len:2281
    truncating very large reference list for doi:10.1017/chol9780521263351.011 len:3129
    truncating very large reference list for doi:10.1017/chol9780521263351.022 len:2968
    truncating very large reference list for doi:10.1017/chol9780521264303.036 len:2221
    truncating very large reference list for doi:10.1017/chol9780521264303.007 len:2238
    truncating very large reference list for doi:10.1017/chol9780521086912.001 len:2177
    truncating very large reference list for doi:10.1017/chol9780521228046.002 len:2133
    truncating very large reference list for doi:10.1017/chol9780521264303.035 len:2221
    truncating very large reference list for doi:10.1017/chol9780521264303.002 len:2279

Seems like bumping to 2500 as the maximum reference list size might be
reasonable (it is 2000 currently).

After some refactoring, still getting:

    requests.exceptions.ConnectionError

This is because I am doing POST without a session.

Then, still got requests.exceptions.ReadTimeout

Finally, got through the whole batch, (`18.6M 8:35:02 [ 603 /s]` output), with
only a few dozen rows like:

    GROBID returned bad XML for Crossref DOI: 10.1007/978-3-030-03008-7_21-1
    GROBID HTTP timeout for Crossref DOI: 10.1007/978-1-4757-1496-8_3
    GROBID HTTP timeout for Crossref DOI: 10.1007/978-1-4757-1493-7_3
    GROBID returned bad XML for Crossref DOI: 10.1007/978-3-319-96184-2_2
    GROBID returned bad XML for Crossref DOI: 10.1063/1.5031970
    truncating very large reference list for doi:10.1007/978-1-4757-1499-9_15 len:11401
    GROBID returned bad XML for Crossref DOI: 10.1016/j.oraloncology.2019.104562
    GROBID returned bad XML for Crossref DOI: 10.1016/j.pec.2020.04.010

So things seem to be working!

Summary lines looked like:

    JSON lines pushed: Counter({'total': 531487, 'pushed': 531487})
    Worker: Counter({'total': 536541, 'failed': 3})

Failures per batch were on the order of 0 to 3.
