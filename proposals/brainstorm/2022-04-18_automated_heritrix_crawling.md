
status: brainstorming

We continue to see issues with heritrix3-based crawling. Would like to have an
option to switch to higher-throughput heritrix-based crawling.

SPNv2 path would stick around at least for save-paper-now style ingest.


## Sketch

Ingest requests are created continuously by fatcat, with daily spikes.

Ingest workers run mostly in "bulk" mode, aka they don't make SPNv2 calls.
`no-capture` responses are recorded in sandcrawler SQL database.

Periodically (daily?), a script queries for new no-capture results, filtered to
the most recent period. These are processed in a bit in to a URL list, then
converted to a heritrix frontier, and sent to crawlers. This could either be an
h3 instance (?), or simple `scp` to a running crawl directory.

The crawler crawls, with usual landing page config, and draintasker runs.

TODO: can we have draintasker/heritrix set a maximum WARC life? Like 6 hours?
or, target a smaller draintasker item size, so they get updated more frequently

Another SQL script dumps ingest requests from the *previous* period, and
re-submits them for bulk-style ingest (by workers).

The end result would be things getting crawled and updated within a couple
days.


## Sketch 2

Upload URL list to petabox item, wait for heritrix derive to run (!)
