
import json
import psycopg2
import psycopg2.extras
import requests

class SandcrawlerPostgrestClient:

    def __init__(self, api_url="http://aitio.us.archive.org:3030", **kwargs):
        self.api_uri = api_url

    def get_cdx(self, url):
        resp = requests.get(self.api_url + "/cdx", params=dict(url='eq.'+url))
        resp.raise_for_status()
        return resp.json() or None

    def get_grobid(self, sha1):
        resp = requests.get(self.api_url + "/grobid", params=dict(sha1hex='eq.'+sha1))
        resp.raise_for_status()
        resp = resp.json()
        if resp:
            return resp[0]
        else:
            return None

    def get_file_meta(self, sha1):
        resp = requests.get(self.api_url + "/file_meta", params=dict(sha1hex='eq.'+sha1))
        resp.raise_for_status()
        resp = resp.json()
        if resp:
            return resp[0]
        else:
            return None

class SandcrawlerPostgresClient:

    def __init__(self, db_url, **kwargs):
        self.conn = psycopg2.connect(db_url)

    def cursor(self):
        return self.conn.cursor()

    def commit(self):
        return self.conn.commit()

    def insert_cdx(self, cur, batch, on_conflict="NOTHING"):
        sql = """
            INSERT INTO
            cdx (url, datetime, sha1hex, mimetype, warc_path, warc_csize, warc_offset)
            VALUES %s
            ON CONFLICT ON CONSTRAINT cdx_pkey DO {}
            RETURNING 1;
        """.format(on_conflict)
        batch = [d for d in batch if d.get('warc_offset')]
        if not batch:
            return 0
        batch = [(d['url'],
                  d['datetime'],
                  d['sha1hex'],
                  d['mimetype'],
                  d['warc_path'],
                  d['warc_csize'],
                  d['warc_offset'])
                 for d in batch]
        res = psycopg2.extras.execute_values(cur, sql, batch) # fetch=True
        #return len(res)

    def insert_file_meta(self, cur, batch, on_conflict="NOTHING"):
        sql = """
            INSERT INTO
            file_meta(sha1hex, sha256hex, md5hex, size_bytes, mimetype)
            VALUES %s
            ON CONFLICT (sha1hex) DO {};
        """.format(on_conflict)
        batch = [(d['sha1hex'],
                  d['sha256hex'],
                  d['md5hex'],
                  int(d['size_bytes']),
                  d['mimetype'])
                 for d in batch]
        res = psycopg2.extras.execute_values(cur, sql, batch)

    def insert_grobid(self, cur, batch, on_conflict="NOTHING"): # XXX
        sql = """
            INSERT INTO
            grobid (sha1hex, grobid_version, status_code, status, fatcat_release, metadata)
            VALUES %s
            ON CONFLICT (sha1hex) DO {};
        """.format(on_conflict)
        for r in batch:
            if r.get('metadata'):
                r['metadata'] = json.dumps(r['metadata'], sort_keys=True)
        batch = [(d['key'],
                  d.get('grobid_version') or None,
                  d['status_code'],
                  d['status'],
                  d.get('fatcat_release') or None,
                  d.get('metadata') or None ,
                 )
                 for d in batch]
        res = psycopg2.extras.execute_values(cur, sql, batch)

    def insert_ingest_request(self, cur, batch, on_conflict="NOTHING"):
        sql = """
            INSERT INTO
            ingest_request (link_source, link_source_id, ingest_type, base_url, ingest_request_source, release_stage, request, metadata)
            VALUES %s
            ON CONFLICT ON CONSTRAINT ingest_request_pkey DO {};
        """.format(on_conflict)
        for r in batch:
            if r.get('metadata'):
                r['metadata'] = json.dumps(r['metadata'], sort_keys=True)
        batch = [(d['link_source'],
                  d['link_source_id'],
                  d['ingest_type'],
                  d['base_url'],
                  d.get('ingest_request_source'),
                  d.get('release_stage') or None,
                  d.get('request') or None,
                 )
                 for d in batch]
        res = psycopg2.extras.execute_values(cur, sql, batch)

    def insert_ingest_file_result(self, cur, batch, on_conflict="NOTHING"):
        sql = """
            INSERT INTO
            ingest_file_result (ingest_type, base_url, hit, status, terminal_url, terminal_dt, terminal_status_code, terminal_sha1hex)
            VALUES %s
            ON CONFLICT DO {};
        """.format(on_conflict)
        batch = [(d['ingest_type'],
                  d['base_url'],
                  bool(d['hit']),
                  d['status'],
                  d.get('terminal_url'),
                  d.get('terminal_dt'),
                  d.get('terminal_status_code'),
                  d.get('terminal_sha1hex'),
                 )
                 for d in batch]
        res = psycopg2.extras.execute_values(cur, sql, batch)
