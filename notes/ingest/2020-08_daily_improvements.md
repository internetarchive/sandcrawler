
Goal is to increase rate of successful daily changelog crawling, but reduce
wasted attempts.

Status by domain, past 30 days:

                    domain                |     status      | count 
    --------------------------------------+-----------------+-------
     arxiv.org                            | success         | 21792
     zenodo.org                           | success         | 10646
     res.mdpi.com                         | success         | 10449
     springernature.figshare.com          | no-pdf-link     | 10430
     s3-eu-west-1.amazonaws.com           | success         |  8966
     zenodo.org                           | no-pdf-link     |  8137
     hkvalidate.perfdrive.com             | no-pdf-link     |  5943
     www.ams.org:80                       | no-pdf-link     |  5799
     assets.researchsquare.com            | success         |  4651
     pdf.sciencedirectassets.com          | success         |  4145
     fjfsdata01prod.blob.core.windows.net | success         |  3500
     sage.figshare.com                    | no-pdf-link     |  3174
     onlinelibrary.wiley.com              | no-pdf-link     |  2869
     www.e-periodica.ch                   | no-pdf-link     |  2709
     revistas.uned.es                     | success         |  2631
     figshare.com                         | no-pdf-link     |  2500
     www.sciencedirect.com                | link-loop       |  2477
     linkinghub.elsevier.com              | gateway-timeout |  1878
     downloads.hindawi.com                | success         |  1819
     www.scielo.br                        | success         |  1691
     jps.library.utoronto.ca              | success         |  1590
     www.ams.org                          | no-pdf-link     |  1568
     digi.ub.uni-heidelberg.de            | no-pdf-link     |  1496
     research-repository.griffith.edu.au  | success         |  1412
     journals.plos.org                    | success         |  1330
    (25 rows)

Status by DOI prefix, past 30 days:

     doi_prefix |         status          | count 
    ------------+-------------------------+-------
     10.6084    | no-pdf-link             | 14410   <- figshare; small fraction success
     10.6084    | success                 |  4007
     10.6084    | cdx-error               |  1746

     10.13140   | gateway-timeout         |  9689   <- researchgate
     10.13140   | cdx-error               |  4154

     10.5281    | success                 |  9408   <- zenodo
     10.5281    | no-pdf-link             |  6079
     10.5281    | cdx-error               |  3200
     10.5281    | wayback-error           |  2098

     10.1090    | no-pdf-link             |  7420   <- AMS (ams.org)

     10.3390    | success                 |  6599   <- MDPI
     10.3390    | cdx-error               |  3032
     10.3390    | wayback-error           |  1636

     10.1088    | no-pdf-link             |  3227   <- IOP science

     10.1101    | gateway-timeout         |  3168   <- coldspring harbor: press, biorxiv, medrxiv, etc
     10.1101    | cdx-error               |  1147

     10.21203   | success                 |  3124   <- researchsquare
     10.21203   | cdx-error               |  1181

     10.1016    | success                 |  3083   <- elsevier
     10.1016    | cdx-error               |  2465
     10.1016    | gateway-timeout         |  1682
     10.1016    | wayback-error           |  1567

     10.25384   | no-pdf-link             |  3058   <- sage figshare
     10.25384   | success                 |  2456

     10.1007    | gateway-timeout         |  2913   <- springer
     10.1007    | cdx-error               |  1164

     10.5944    | success                 |  2831
     10.1186    | success                 |  2650
     10.5169    | no-pdf-link             |  2644   <- www.e-periodica.ch
     10.3389    | success                 |  2279
     10.24411   | gateway-timeout         |  2184   <- cyberleninka.ru
     10.1038    | gateway-timeout         |  2143   <- nature group
     10.1177    | gateway-timeout         |  2038   <- SAGE
     10.11588   | no-pdf-link             |  1574   <- journals.ub.uni-heidelberg.de (OJS?)
     10.25904   | success                 |  1416
     10.1155    | success                 |  1304
     10.21994   | no-pdf-link             |  1268   <- loar.kb.dk
     10.18720   | spn2-cdx-lookup-failure |  1232   <- elib.spbstu.ru
     10.24411   | cdx-error               |  1202
     10.1055    | no-pdf-link             |  1170   <- thieme-connect.de
    (40 rows)

code changes for ingest:
x hkvalidate.perfdrive.com: just bail when we see this
x skip large publishers which gateway-timeout (for now)
    - springerlink (10.1007)
    - nature group (10.1038)
    - SAGE (10.1177)
    - IOP (10.1088)

fatcat:
x figshare (by `doi_prefix`): if not versioned (suffix), skip crawl
x zenodo: also try to not crawl if unversioned (group)
x figshare import metadata

sandcrawler:
x ends with `cookieAbsent` or `cookieSet=1` -> status as cookie-blocked
x https://profile.thieme.de/HTML/sso/ejournals/login.htm[...] => blocklist
x verify that we do quick-get for arxiv.org + europmc.org (+ figshare/zenodo?)
    => we were not!
x shorten post-SPNv2 CDX pause? for throughput, given that we are re-trying anyways
x ensure that we store uncrawled URL somewhere on no-capture status
    => in HTML or last of hops
    => not in DB, but that is a bigger change

- try to get un-blocked:
    - coldspring harbor has been blocking since 2020-06-22? yikes!
    - cyberleninka.ru
    - arxiv.org

- no-pdf-link
    x www.ams.org (10.1090)
        => these seem to be stale captures, eg from 2008. newer captures have citation_pdf_url
        => should consider recrawling all of ams.org?
        => not sure why these crawl requests are happening only now
        => on the order of 15k OA articles not in ia; 43k total not preserved
        => force recrawl OA subset (DONE)
    x www.e-periodica.ch (10.5169)
        => TODO: dump un-preserved URLs, transform to PDF urls, heritrix crawl, re-ingest
    x digi.ub.uni-heidelberg.de (10.11588)
        => TODO: bulk re-enqueue? then heritrix crawl?
    - https://loar.kb.dk/handle/1902/6988 (10.21994)
        => TODO: bulk re-enqueue
        => site was updated recently (august 2020); now it crawls fine. need to re-ingest all?
        => 7433 hits
    - thieme-connect.de (10.1055)
        => 600k+ missing
        => TODO: bulk re-enqueue? then heritrix crawl?
        => https://profile.thieme.de/HTML/sso/ejournals/login.htm[...] => blocklist
        => generally just need to re-crawl all?

Unresolved:
- why so many spn2-errors on https://elib.spbstu.ru/ (10.18720)?

## figshare

10.6084     regular figshare
10.25384    SAGE figshare

For sage, "collections" are bogus? can we detect these in datacite metadata?

If figshare types like:

    ris: "GEN",
    bibtex: "misc",
    citeproc: "article",
    schemaOrg: "Collection",
    resourceType: "Collection",
    resourceTypeGeneral: "Collection"

then mark as 'stub'.

"Additional file" items don't seem like "stub"; -> "component".

title:"Figure {} from " -> component

current types are mostly: article, stub, dataset, graphic, article-journal

If DOI starts with "sage.", then publisher is "Sage" (not figshare). Container
name should be... sage.figshare.com?

set version to the version from DOI

## zenodo

doi_prefix: 10.5281

if on zenodo, and has a "Identical to" relation, then this is a pre-print. in
that case, drop container_id and set container_name to zenodo.org. *But*, there
are some journals now publishing exclusively to zenodo.org, so retain that
metadata. examples:

    "Detection of keyboard vibrations and effects on perceived piano quality"
    https://fatcat.wiki/release/mufzkdgt2nbzfha44o7p7gkrpy

    "Editing LAF: Educate, don't defend!"
    https://zenodo.org/record/2583025

version number not available in zenodo metadata

## Gitlab MR Notes

The main goal of this group of changes is to do a better job at daily ingest.

Currently we have on the order of 20k new releases added to the index every day, and about half of them get are marked as OA (either CC license or via container being in DOAJ or ROAD), and pass some filters (eg, release_type), and are selected for ingest. Of those, about half fail to crawl to fulltext, either due to blocking (gateway-timeout, cookie tests, anti-bot detection, loginwall, etc). On the other hand, we don't attempt to crawl lots of "bronze" OA, which is content that is available from the publisher website, but isn't marked explicitly OA.

Based on investigating daily crawling from the past month (will commit these notes to sandcrawler soon), I have identified some DOI prefixes that almost always fail ingest via SPNv2. I also have some patches to sandcrawler ingest to improve ability to crawl some large repositories etc.

Some of the biggest "OA but failed to crawl" are from figshare and zenodo, which register a relatively large fraction of daily OA DOIs. We want to crawl most of that content, but both of these platforms register at least DOIs for each piece of content (a "group" DOI and a "versioned" DOI), and we only need to crawl one. There were also some changes needed to release-type filtering and assignment specific to these platforms, or based on the title of entities.

This MR mixes changes to the datacite metadata import routing (including some refactors out of the main parse_record method) and behavior changes to the entity updater (which is where the code to decide about whether to send an ingest request on release creation lives). I will have a separate MR for importer metadata changes that don't impact ingest behavior.

