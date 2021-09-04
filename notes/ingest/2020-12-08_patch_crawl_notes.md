
Notes here about re-ingesting or re-crawling large batches. Goal around end of
2020 is to generate a broad patch crawl of terminal no-capture attempts for all
major sources crawled thus far. Have already tried run this process for unpaywall.

For each, want filtered ingest request JSON objects (filtering out platforms
that don't crawl well, and possibly things like figshare+zenodo), and a broader
seedlist (including terminal URLs). Will de-dupe all the seedlist URLs and do a
heritrix crawl with new config, then re-ingest all the requests individually.

Summary of what to do here:

    OA DOI: expecting some 2.4 million seeds
    OAI-PMH: expecting some 5 million no-capture URLs, plus more from missing PDF URL not found
    Unpaywall: another ~900k no-capture URLs (maybe filtered?)

For all, re-attempt for these status codes:

     no-capture
     cdx-error
     wayback-error
     petabox-error
     gateway-timeout (?)

And at least do bulk re-ingest for these, if updated before 2020-11-20 or so:

     no-pdf-link

## OAI-PMH

Need to re-ingest all of the (many!) no-capture and no-pdf-link

TODO: repec-specific URL extraction?

Skip these OAI prefixes:

     kb.dk
     bnf.fr
     hispana.mcu.es
     bdr.oai.bsb-muenchen.de
     ukm.si
     hsp.org

Skip these domains:

    www.kb.dk (kb.dk)
    kb-images.kb.dk (kb.dk)
    mdz-nbn-resolving.de (TODO: what prefix?)
    aggr.ukm.um.si (ukm.si)

Check PDF link extraction for these prefixes, or skip them (TODO):

    repec (mixed success)
    biodiversitylibrary.org
    juser.fz-juelich.de
    americanae.aecid.es
    www.irgrid.ac.cn
    hal
    espace.library.uq.edu.au
    igi.indrastra.com
    invenio.nusl.cz
    hypotheses.org
    t2r2.star.titech.ac.jp
    quod.lib.umich.edu

    domain: hemerotecadigital.bne.es
    domain: bib-pubdb1.desy.de
    domain: publikationen.bibliothek.kit.edu
    domain: edoc.mpg.de
    domain: bibliotecadigital.jcyl.es
    domain: lup.lub.lu.se
    domain: orbi.uliege.be

TODO:
- consider deleting ingest requests from skipped prefixes (large database use)


## Unpaywall

About 900k `no-pdf-link`, and up to 2.5 million more `no-pdf-link`.

Re-bulk-ingest filtered requests which hit `no-pdf-link` before 2020-11-20:

    COPY (
        SELECT row_to_json(ingest_request.*)
        FROM ingest_request
        LEFT JOIN ingest_file_result
            ON ingest_file_result.ingest_type = ingest_request.ingest_type
            AND ingest_file_result.base_url = ingest_request.base_url
        WHERE
            ingest_request.ingest_type = 'pdf'
            AND ingest_request.link_source = 'unpaywall'
            AND date(ingest_request.created) < '2020-11-20'
            AND ingest_file_result.status = 'no-pdf-link'
            AND ingest_request.base_url NOT LIKE '%journals.sagepub.com%'
            AND ingest_request.base_url NOT LIKE '%pubs.acs.org%'
            AND ingest_request.base_url NOT LIKE '%ahajournals.org%'
            AND ingest_request.base_url NOT LIKE '%www.journal.csj.jp%'
            AND ingest_request.base_url NOT LIKE '%aip.scitation.org%'
            AND ingest_request.base_url NOT LIKE '%academic.oup.com%'
            AND ingest_request.base_url NOT LIKE '%tandfonline.com%'
            AND ingest_request.base_url NOT LIKE '%://archive.org/%'
            AND ingest_request.base_url NOT LIKE '%://web.archive.org/%'
            AND ingest_request.base_url NOT LIKE '%://www.archive.org/%'
    ) TO '/grande/snapshots/unpaywall_nopdflink_2020-12-08.rows.json';
    => COPY 1309990

    ./scripts/ingestrequest_row2json.py /grande/snapshots/unpaywall_nopdflink_2020-12-08.rows.json | pv -l | shuf > /grande/snapshots/unpaywall_nopdflink_2020-12-08.ingest_request.json
    => 1.31M 0:00:51 [25.6k/s]

    cat /grande/snapshots/unpaywall_nopdflink_2020-12-08.rows.json | rg -v "\\\\" | jq . -c | kafkacat -P -b wbgrp-svc263.us.archive.org -t sandcrawler-prod.ingest-file-requests-bulk -p -1
