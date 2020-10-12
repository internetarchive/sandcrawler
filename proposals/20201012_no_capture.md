
status: in-progress

Storing no-capture missing URLs in `terminal_url`
=================================================

Currently, when the bulk-mode ingest code terminates with a `no-capture`
status, the missing URL (which is not in GWB CDX) is not stored in
sandcrawler-db. This proposed change is to include it in the existing
`terminal_url` database column, with the `terminal_status_code` and
`terminal_dt` columns empty.

The implementation is rather simple:

- CDX lookup code path should save the *actual* final missing URL (`next_url`
  after redirects) in the result object's `terminal_url` field
- ensure that this field gets passed through all the way to the database on the
  `no-capture` code path

This change does change the semantics of the `terminal_url` field somewhat, and
could break existing assumptions, so it is being documented in this proposal
document.


## Alternatives

The current status quo is to store the missing URL as the last element in the
"hops" field of the JSON structure. We could keep this and have a convoluted
pipeline that would read from the Kafka feed and extract them, but this would
be messy. Eg, re-ingesting would not update the old kafka messages, so we could
need some accounting of consumer group offsets after which missing URLs are
truely missing.

We could add a new `missing_url` database column and field to the JSON schema,
for this specific use case. This seems like unnecessary extra work.

