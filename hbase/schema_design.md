
## PDF Table

Table name: `wbgrp-journal-extract-<version>-<env>`

Eg: `wbgrp-journal-extract-0-prod`

Key is the sha1 of the file, as raw bytes (20 bytes).

Could conceivably need to handle, eg, postscript files, JATS XML, or even HTML
in the future? If possible be filetype-agnostic, but only "fulltext" file types
will end up in here, and don't bend over backwards.

Keep only a single version (do we need `VERSIONS => 1`, or is 1 the default?)

IMPORTANT: column names should be unique across column families. Eg, should not
have both `grobid0:status` and `match0:status`. HBase and some client libraries
don't care, but some map/reduce frameworks (eg, Scalding) can have name
collisions. Differences between "orthogonal" columns *might* be OK (eg,
`grobid0:status` and `grobid1:status`).

Column families:

- `key`: sha1 of the file in base32 (not a column or column family)
- `f`: heritrix HBaseContentDigestHistory de-dupe
    - `c`: (json string)
        - `u`: original URL (required)
        - `d`: original date (required; ISO 8601:1988)
        - `f`: warc filename (recommend)
        - `o`: warc offset (recommend)
        - `c`: dupe count (optional)
        - `i`: warc record ID (optional)
- `file`: crawl and file metadata
    - `size` (uint64), uncompressed (not in CDX)
    - `mime` (string; might do postscript in the future; normalized)
    - `cdx` (json string) with all as strings
        - `surt`
        - `url`
        - `dt`
        - `warc` (item and file name)
        - `offset`
        - `c_size` (compressed size)
- `grobid0`: processing status, version, XML and JSON fulltext, JSON metadata. timestamp. Should be compressed! `COMPRESSION => SNAPPY`
    - `status_code` (signed int; HTTP status from grobid)
    - `quality` (int or string; we define the meaning ("good"/"marginal"/"bad")
    - `status` (json string from grobid)
    - `tei_xml` (xml string from grobid)
    - `tei_json` (json string with fulltext)
    - `metadata` (json string with author, title, abstract, citations, etc)
- `match0`: status of identification against "the catalog"
    - `mstatus` (string; did it match?)
    - `doi` (string)
    - `minfo` (json string)

Can add additional groups in the future for additional processing steps. For
example, we might want to do first pass looking at files to see "is this a PDF
or not", which out output some status (and maybe certainty).

The Heritrix schema is fixed by the existing implementation. We could
patch/extend heritrix to use the `file` schema in the future if we decide
it's worth it. There are some important pieces of metadata missing, so at
least to start I think we should keep `f` and `file` distinct. We could merge
them later. `f` info will be populated by crawlers; `file` info should be
populated when back-filling or processing CDX lines.

If we wanted to support multiple CDX rows as part of the same row (eg, as
alternate locations), we could use HBase's versions feature, which can
automatically cap the number of versions stored.

If we had enough RAM resources, we could store `f` (and maybe `file`) metadata
in memory for faster access.
