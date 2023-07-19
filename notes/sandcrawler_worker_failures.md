# Sandcrawler worker failures

Failed services, logs, etc.

## 2023-07-15

```
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]: [FETCH wayback] success  https://www.mdpi.com/2072-4292/15/5/1253
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:   transfer encoding not stripped: text/html
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]: /1/srv/sandcrawler/src/python/.venv/lib/python3.8/site-packages/dateparser/date_parser.py:35: PytzUsageWarning: The localize method is no longer necessary, as this t>
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:   date_obj = stz.localize(date_obj)
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]: [PARSE     pdf] html_biblio  https://www.mdpi.com/2072-4292/15/5/1253/pdf?version=1677241977
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:   URL: https://www.mdpi.com/2072-4292/15/5/1253/pdf?version=1677241977
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]: WARNING:root:first line b'' does not seem to be a chunk size
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]: Traceback (most recent call last):
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:   File "./sandcrawler_worker.py", line 495, in <module>
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:     main()
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:   File "./sandcrawler_worker.py", line 491, in main
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:     args.func(args)
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:   File "./sandcrawler_worker.py", line 286, in run_ingest_file
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:     pusher.run()
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:   File "/1/srv/sandcrawler/src/python/sandcrawler/workers.py", line 578, in run
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:     self.worker.push_record_timeout(
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:   File "/1/srv/sandcrawler/src/python/sandcrawler/workers.py", line 79, in push_record_timeout
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:     resp = self.push_record(task, key=key)
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:   File "/1/srv/sandcrawler/src/python/sandcrawler/workers.py", line 39, in push_record
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:     result = self.process(task, key=key)
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:   File "/1/srv/sandcrawler/src/python/sandcrawler/ingest_file.py", line 574, in process
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:     return self.process_file(request, key=key)
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:   File "/1/srv/sandcrawler/src/python/sandcrawler/ingest_file.py", line 644, in process_file
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:     resource = self.find_resource(
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:   File "/1/srv/sandcrawler/src/python/sandcrawler/ingest_file.py", line 268, in find_resource
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:     resource = self.wayback_client.lookup_resource(url, best_mimetype)
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:   File "/1/srv/sandcrawler/src/python/sandcrawler/ia.py", line 809, in lookup_resource
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:     resource = self.fetch_petabox(
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:   File "/1/srv/sandcrawler/src/python/sandcrawler/ia.py", line 535, in fetch_petabox
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]:     assert len(revisit_dt) in (19, 20)
Jul 15 07:31:05 wbgrp-svc506.us.archive.org sandcrawler-ingest[1180367]: AssertionError
Jul 15 07:31:05 wbgrp-svc506.us.archive.org systemd[1]: sandcrawler-ingest-file-worker@11.service: Main process exited, code=exited, status=1/FAILURE
```
