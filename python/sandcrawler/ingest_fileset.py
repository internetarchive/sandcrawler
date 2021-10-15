
import sys
import json
import gzip
import time
from collections import namedtuple
from typing import Optional, Tuple, Any, Dict, List

import requests
from selectolax.parser import HTMLParser

from sandcrawler.ia import SavePageNowClient, CdxApiClient, WaybackClient, WaybackError, WaybackContentError, SavePageNowError, CdxApiError, PetaboxError, cdx_to_dict, ResourceResult, fix_transfer_encoding, NoCaptureError
from sandcrawler.misc import gen_file_metadata, clean_url, parse_cdx_datetime
from sandcrawler.html import extract_fulltext_url
from sandcrawler.ingest_html import fetch_html_resources, \
    quick_fetch_html_resources, html_guess_scope, html_extract_body_teixml, \
    WebResource, html_guess_platform

from sandcrawler.html_metadata import BiblioMetadata, html_extract_resources, html_extract_biblio, load_adblock_rules
from sandcrawler.workers import SandcrawlerWorker
from sandcrawler.db import SandcrawlerPostgrestClient
from sandcrawler.ingest_file import IngestFileWorker
from sandcrawler.fileset_platforms import FilesetPlatformHelper, DATASET_PLATFORM_HELPER_TABLE
from sandcrawler.fileset_strategies import FilesetIngestStrategy, FILESET_STRATEGY_HELPER_TABLE
from sandcrawler.fileset_types import PlatformScopeError, PlatformRestrictedError


MAX_BODY_SIZE_BYTES = 128*1024*1024

class IngestFilesetWorker(IngestFileWorker):
    """
    General process is:

    1. crawl base_url, and use request and landing page resource (eg, HTML) to
       determine platform being targeted
    2. use platform-specific helper to fetch metadata about the work, including
       a manifest of files, and selection of an "ingest strategy" and any
       required context
    3. then use strategy-specific helper to archive files from manifest (first
       checking to see if content has been archived already)
    4. summarize status
    """

    def __init__(self, sink=None, **kwargs):
        super().__init__(sink=None, **kwargs)

        self.sink = sink
        self.dataset_platform_helpers = DATASET_PLATFORM_HELPER_TABLE
        self.dataset_strategy_archivers = FILESET_STRATEGY_HELPER_TABLE
        self.max_total_size = kwargs.get('max_total_size', 64*1024*1024*1024)
        self.max_file_count = kwargs.get('max_file_count', 200)


    def check_existing_ingest(self, ingest_type: str, base_url: str) -> Optional[dict]:
        """
        Same as file version, but uses fileset result table
        """
        if not self.try_existing_ingest:
            return None
        existing = self.pgrest_client.get_ingest_fileset_result(ingest_type, base_url)
        # TODO: filter on more flags?
        if existing and existing['hit'] == True:
            return existing
        else:
            return None

    def process_existing(self, request: dict, result_row: dict) -> dict:
        """
        If we have an existing ingest fileset result, do any database fetches
        or additional processing necessary to return a result.
        """
        raise NotImplementedError("process_existing() not tested or safe yet")

    # XXX: use file version
    #def process_hit(self, ingest_type: str, resource: ResourceResult, file_meta: dict) -> dict:

    def want(self, request: dict) -> bool:
        if not request.get('ingest_type') in ('dataset',):
            return False
        return True

    def fetch_resource_iteratively(self, ingest_type: str, base_url: str, force_recrawl: bool) -> dict:
        """
        This is copypasta from process_file(), should probably refactor.
        """

        result: Dict[str, Any] = dict(hit=False)
        result['hops'] = [base_url]
        next_url = base_url

        # check against blocklist
        for block in self.base_url_blocklist:
            # XXX: hack to not skip archive.org content
            if 'archive.org' in block:
                continue
            if block in next_url:
                result['status'] = "skip-url-blocklist"
                return result

        try:
            resource = self.find_resource(next_url, force_recrawl=force_recrawl)
        except SavePageNowError as e:
            result['status'] = 'spn2-error'
            result['error_message'] = str(e)[:1600]
            return result
        except PetaboxError as e:
            result['status'] = 'petabox-error'
            result['error_message'] = str(e)[:1600]
            return result
        except CdxApiError as e:
            result['status'] = 'cdx-error'
            result['error_message'] = str(e)[:1600]
            # add a sleep in cdx-error path as a slow-down
            time.sleep(2.0)
            return result
        except WaybackError as e:
            result['status'] = 'wayback-error'
            result['error_message'] = str(e)[:1600]
            return result
        except WaybackContentError as e:
            result['status'] = 'wayback-content-error'
            result['error_message'] = str(e)[:1600]
            return result
        except NotImplementedError as e:
            #result['status'] = 'not-implemented'
            #result['error_message'] = str(e)[:1600]
            #return result
            resource = None

        html_biblio = None
        if resource:
            if resource.terminal_url:
                result['terminal'] = {
                    "terminal_url": resource.terminal_url,
                    "terminal_dt": resource.terminal_dt,
                    "terminal_status_code": resource.terminal_status_code,
                }
                if resource.terminal_url not in result['hops']:
                    result['hops'].append(resource.terminal_url)

            if not resource.hit:
                result['status'] = resource.status
                return result

            if resource.terminal_url:
                for pattern in self.base_url_blocklist:
                    if pattern in resource.terminal_url:
                        result['status'] = 'skip-url-blocklist'
                        return result

            if resource.terminal_url:
                for pattern in self.cookie_blocklist:
                    if pattern in resource.terminal_url:
                        result['status'] = 'blocked-cookie'
                        return result

            if not resource.body:
                result['status'] = 'null-body'
                return result

            if len(resource.body) > MAX_BODY_SIZE_BYTES:
                result['status'] = 'body-too-large'
                return result

            file_meta = gen_file_metadata(resource.body)
            try:
                file_meta, resource = fix_transfer_encoding(file_meta, resource)
            except Exception as e:
                result['status'] = 'bad-gzip-encoding'
                result['error_message'] = str(e)
                return result

            if not resource.body or file_meta['size_bytes'] == 0:
                result['status'] = 'null-body'
                return result

            # here we split based on ingest type to try and extract a next hop
            html_ish_resource = bool(
                "html" in file_meta['mimetype']
                or "xhtml" in file_meta['mimetype'] # matches "application/xhtml+xml"
                or "application/xml" in file_meta['mimetype']
                or "text/xml" in file_meta['mimetype']
            )
            html_biblio = None
            html_doc = None
            if html_ish_resource and resource.body:
                try:
                    html_doc = HTMLParser(resource.body)
                    html_biblio = html_extract_biblio(resource.terminal_url, html_doc)
                    if html_biblio:
                        if not 'html_biblio' in result or html_biblio.title:
                            result['html_biblio'] = json.loads(html_biblio.json(exclude_none=True))
                            #print(f"  setting html_biblio: {result['html_biblio']}", file=sys.stderr)
                except ValueError:
                    pass

            # fetch must be a hit if we got this far (though not necessarily an ingest hit!)
            assert resource
            assert resource.hit == True
            assert resource.terminal_status_code in (200, 226)

            if resource.terminal_url:
                result['terminal'] = {
                    "terminal_url": resource.terminal_url,
                    "terminal_dt": resource.terminal_dt,
                    "terminal_status_code": resource.terminal_status_code,
                    "terminal_sha1hex": file_meta['sha1hex'],
                }

            result['file_meta'] = file_meta
            result['cdx'] = cdx_to_dict(resource.cdx)
            if resource.revisit_cdx:
                result['revisit_cdx'] = cdx_to_dict(resource.revisit_cdx)

            if ingest_type == "pdf":
                if file_meta['mimetype'] != "application/pdf":
                    result['status'] = "wrong-mimetype"  # formerly: "other-mimetype"
                    return result
            elif ingest_type == "xml":
                if file_meta['mimetype'] not in ("application/xml", "text/xml", "application/jats+xml"):
                    result['status'] = "wrong-mimetype"
                    return result
            elif ingest_type == "html":
                if file_meta['mimetype'] not in ("text/html", "application/xhtml+xml"):
                    result['status'] = "wrong-mimetype"
                    return result
            else:
                #raise NotImplementedError()
                pass

        result['_html_biblio'] = html_biblio
        result['_resource'] = resource
        return result


    def process(self, request: dict, key: Any = None) -> dict:

        ingest_type = request.get('ingest_type')
        if ingest_type not in ("dataset",):
            raise NotImplementedError(f"can't handle ingest_type={ingest_type}")

        # parse/clean URL
        # note that we pass through the original/raw URL, and that is what gets
        # persisted in database table
        base_url = clean_url(request['base_url'])

        force_recrawl = bool(request.get('force_recrawl', False))

        print("[INGEST {:>6}] {}".format(ingest_type, base_url), file=sys.stderr)

        # TODO: "existing" check against file and/or fileset ingest result table
        #existing = self.check_existing_ingest(ingest_type, base_url)
        #if existing:
        #    return self.process_existing(request, existing)

        result = self.fetch_resource_iteratively(ingest_type, base_url, force_recrawl=force_recrawl)
        if result.get('status') != None:
            result['request'] = request
            return result

        html_biblio = result.pop('_html_biblio')
        resource = result.pop('_resource')

        # 1. Determine `platform`, which may involve resolving redirects and crawling a landing page.

        # TODO: could involve html_guess_platform() here?

        # determine platform
        platform_helper = None
        for (helper_name, helper) in self.dataset_platform_helpers.items():
            if helper.match_request(request, resource, html_biblio):
                platform_helper = helper
                break

        if not platform_helper:
            result['status'] = 'no-platform-match'
            return result

        # 2. Use platform-specific methods to fetch manifest metadata and decide on an `ingest_strategy`.
        terminal_url = base_url
        if resource:
            terminal_url = resource.terminal_url

        try:
            dataset_meta = platform_helper.process_request(request, resource, html_biblio)
        except PlatformScopeError as e:
            result['status'] = 'platform-scope'
            result['error_message'] = str(e)[:1600]
            return result
        except PlatformRestrictedError as e:
            result['status'] = 'platform-restricted'
            result['error_message'] = str(e)[:1600]
            return result
        except NotImplementedError as e:
            result['status'] = 'not-implemented'
            result['error_message'] = str(e)[:1600]
            return result
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                result['status'] = 'platform-404'
                result['error_message'] = str(e)[:1600]
                return result
            else:
                raise e

        #print(dataset_meta, file=sys.stderr)
        platform = dataset_meta.platform_name
        result['platform_name'] = dataset_meta.platform_name
        result['platform_domain'] = dataset_meta.platform_domain
        result['platform_id'] = dataset_meta.platform_id
        result['archiveorg_item_name'] = dataset_meta.archiveorg_item_name

        if not dataset_meta.manifest:
            result['status'] = 'empty-manifest'
            return result

        # these will get confirmed/updated after ingest
        result['manifest'] = [m.dict() for m in dataset_meta.manifest]
        result['file_count'] = len(dataset_meta.manifest)
        result['total_size'] = sum([m.size for m in dataset_meta.manifest if m.size])

        if result['total_size'] > self.max_total_size:
            result['status'] = 'too-large-size'
            return result
        if result['file_count'] > self.max_file_count:
            # hard max, to prevent downstream breakage
            if result['file_count'] > 10*1000:
                result['manifest'] = result['manifest'][:self.max_file_count]
            result['status'] = 'too-many-files'
            return result

        ingest_strategy = platform_helper.chose_strategy(dataset_meta)
        result['ingest_strategy'] = ingest_strategy
        print(f"[PLATFORM {platform}] id={dataset_meta.platform_id} file_count={result['file_count']} total_size={result['total_size']} strategy={ingest_strategy}", file=sys.stderr)

        strategy_helper = self.dataset_strategy_archivers.get(ingest_strategy)
        if not strategy_helper:
            result['status'] = 'no-strategy-helper'
            return result

        # 3. Use strategy-specific methods to archive all files in platform manifest, and verify manifest metadata.
        archive_result = strategy_helper.process(dataset_meta)

        # 4. Summarize status and return structured result metadata.
        result['status'] = archive_result.status
        result['manifest'] = [m.dict() for m in archive_result.manifest]

        if ingest_strategy.endswith('-fileset-bundle'):
            result['fileset_bundle'] = dict(
                file_meta=archive_result.bundle_file_meta,
                archiveorg_bundle_path=archive_result.archiveorg_bundle_path,
            )
            if archive_result.bundle_terminal:
                result['fileset_bundle']['terminal'] = dict(
                    terminal_url=archive_result.bundle_terminal.terminal_url,
                    terminal_dt=archive_result.bundle_terminal.terminal_dt,
                    terminal_status_code=archive_result.bundle_terminal.terminal_status_code,
                )
            if archive_result.bundle_cdx:
                result['fileset_bundle']['cdx'] = cdx_to_dict(archive_result.bundle_cdx)
                if archive_result.bundle_cdx.revisit_cdx:
                    result['fileset_bundle']['revisit_cdx'] = cdx_to_dict(archive_result.bundle_cdx.revisit_cdx)
        if ingest_strategy.endswith('-file'):
            result['fileset_file'] = dict(
                file_meta=archive_result.file_file_meta,
            )
            if archive_result.file_terminal:
                result['fileset_file']['terminal'] = dict(
                    terminal_url=archive_result.file_terminal.terminal_url,
                    terminal_dt=archive_result.file_terminal.terminal_dt,
                    terminal_status_code=archive_result.file_terminal.terminal_status_code,
                )
            if archive_result.file_cdx:
                result['fileset_file']['cdx'] = cdx_to_dict(archive_result.file_cdx)
                if archive_result.file_cdx.revisit_cdx:
                    result['fileset_file']['revisit_cdx'] = cdx_to_dict(archive_result.file_cdx.revisit_cdx)

        if result['status'].startswith('success'):
            # check that these are still valid
            assert result['file_count'] == len(archive_result.manifest)
            assert result['total_size'] == sum([m.size for m in archive_result.manifest if m.size])


        # XXX: here is where we would publish to ingest file result topic... or call process_hit()?
        if result['status'] == 'success-file':
            pass

        if result['status'].startswith('success'):
            result['hit'] = True
            print("[SUCCESS {:>5}] file_count={} total_size={} strategy={}".format(
                    ingest_type,
                    result['file_count'],
                    result['total_size'],
                    ingest_strategy,
                ), file=sys.stderr)
        else:
            print("[FAIL    {:>5}] status={} file_count={} total_size={} strategy={}".format(
                    ingest_type,
                    result['status'],
                    result['file_count'],
                    result['total_size'],
                    ingest_strategy,
                ), file=sys.stderr)
        return result