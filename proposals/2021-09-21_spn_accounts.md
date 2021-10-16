
Formalization of SPNv2 API requests from fatcat/sandcrawler

Create two new system accounts, one for regular/daily ingest requests, one for
priority requests (save-paper-now or as a flag with things like fatcat-ingest;
"interactive"). These accounts should have @archive.org emails. Request the
daily one to have the current rate limit as bnewbold@archive.org account; the
priority queue can have less.

Create new ingest kafka queues from scratch, one for priority and one for
regular. Chose sizes carefully, probably keep 24x for the regular and do 6x or
so (small) for priority queue.

Deploy new priority workers; reconfigure/deploy broadly.
