
status: wip

HTML Ingest Pipeline
========================

Basic goal: given an ingest request of type 'html', output an object (JSON)
which could be imported into fatcat.

Should work with things like (scholarly) blog posts, micropubs, registrations,
protocols. Doesn't need to work with everything to start. "Platform" sites
(like youtube, figshare, etc) will probably be a different ingest worker.

A current unknown is what the expected size of this metadata is. Both in number
of documents and amount of metadata per document.

Example HTML articles to start testing:

- complex distill article: <https://distill.pub/2020/bayesian-optimization/>
- old HTML journal: <http://web.archive.org/web/20081120141926fw_/http://www.mundanebehavior.org/issues/v5n1/rosen.htm>
- NIH pub: <https://www.nlm.nih.gov/pubs/techbull/ja02/ja02_locatorplus_merge.html>
- first mondays (OJS): <https://firstmonday.org/ojs/index.php/fm/article/view/10274/9729>
- d-lib: <http://www.dlib.org/dlib/july17/williams/07williams.html> 


## Ingest Process

Follow base URL to terminal document, which is assumed to be a status=200 HTML document.

Verify that terminal document is fulltext. Extract both metadata and fulltext.

Extract list of sub-resources. Filter out unwanted (eg favicon, analytics,
unnecessary), apply a sanity limit. Convert to fully qualified URLs. For each
sub-resource, fetch down to the terminal resource, and compute hashes/metadata.

Open questions:

- will probably want to parallelize sub-resource fetching. async?
- behavior when failure fetching sub-resources


## Ingest Result Schema

JSON should be basically compatible with existing `ingest_file_result` objects,
with some new sub-objects.

Overall object (`IngestWebResult`):

- `status`: str
- `hit`: bool
- `error_message`: optional, if an error
- `hops`: optional, array of URLs
- `cdx`: optional; single CDX row of primary HTML document
- `terminal`: optional; same as ingest result
    - `terminal_url`
    - `terminal_dt`
    - `terminal_status_code`
    - `terminal_sha1hex`
- `request`: optional but usually present; ingest request object, verbatim
- `file_meta`: optional; file metadata about primary HTML document
- `html_biblio`: optional; extracted biblio metadata from primary HTML document
- `scope`: optional; detected/guessed scope (fulltext, etc)
- `html_resources`: optional; array of sub-resources. primary HTML is not included
- `html_body`: optional; just the status code and some metadata is passed through;
  actual document would go through a different KafkaTopic
    - `status`: str
    - `agent`: str, eg "trafilatura/0.4"
    - `tei_xml`: optional, str
    - `word_count`: optional, str


## New SQL Tables

`html_meta`
    sha1hex (primary key)
    updated (of SQL row)
    status
    scope
    has_teixml
    has_thumbnail
    word_count (from teixml fulltext)
    biblio (JSON)
    resources (JSON)

Also writes to `ingest_file_result`, `file_meta`, and `cdx`, all only for the base HTML document.


## Fatcat API Wants

Would be nice to have lookup by SURT+timestamp, and/or by sha1hex of terminal base file.

`hide` option for cdx rows; also for fileset equivalent.


## New Workers

Could reuse existing worker, have code branch depending on type of ingest.

ingest file worker
  => same as existing worker, because could be calling SPN

persist result
  => same as existing worker; adds persisting various HTML metadata

persist html text
  => talks to seaweedfs


## New Kafka Topics

HTML ingest result topic (webcapture-ish)

sandcrawler-ENV.html-teixml
    JSON wrapping TEI-XML (same as other fulltext topics)
    key compaction and content compression enabled

JSON schema:

- `key` and `sha1hex`: str; used as kafka key
- `status`: str
- `tei_xml`: str, optional
- `word_count`: int, optional

## New S3/SeaweedFS Content

`sandcrawler` bucket, `html` folder, `.tei.xml` suffix.

