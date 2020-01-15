
-- rows *may* be revisit records; indicated by mimetype == "warc/revisit"
-- records are implied to be 200 status (or 226 for ftp); either direct hits or
-- revisits
-- there is nothing to prevent duplicate hits. eg, same sha1, same url, many
-- datetimes. import scripts should take efforts to reduce this sort of
-- duplication though. one row per *domain*/sha1hex pair is a good guideline.
-- all ingest result url/dt pairs should be included though.
-- any mimetype is allowed, but presumption should be that actual body is full
-- manifestation of a work. AKA, no landing pages, no webcapture HTML (each
-- only a part of work). URLs that are parts of a fileset are allowed.
CREATE TABLE IF NOT EXISTS cdx (
    url                 TEXT NOT NULL CHECK (octet_length(url) >= 1),
    datetime            TEXT NOT NULL CHECK (octet_length(datetime) = 14),
    -- sha1hex/cdx_sha1hex difference is intended to help with difference between
    -- CDX hash (which is transport encoded body) vs. actual body. Probably need to
    -- include both for all records?
    sha1hex             TEXT NOT NULL CHECK (octet_length(sha1hex) = 40),
    cdx_sha1hex         TEXT CHECK (octet_length(cdx_sha1hex) = 40),
    mimetype            TEXT CHECK (octet_length(mimetype) >= 1),
    -- TODO: enforce that only paths with '/' (item+file) should be included?
    warc_path           TEXT CHECK (octet_length(warc_path) >= 1),
    warc_csize          BIGINT,
    warc_offset         BIGINT,
    row_created         TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY(url, datetime)
);
CREATE INDEX IF NOT EXISTS cdx_sha1hex_idx ON cdx(sha1hex);
-- TODO: remove this index? not currently used
CREATE INDEX IF NOT EXISTS cdx_row_created_idx ON cdx(row_created);

-- TODO: require all fields. if mimetype unknown, should be octet-stream
CREATE TABLE IF NOT EXISTS file_meta (
    sha1hex             TEXT PRIMARY KEY CHECK (octet_length(sha1hex) = 40),
    sha256hex           TEXT CHECK (octet_length(sha256hex) = 64),
    md5hex              TEXT CHECK (octet_length(md5hex) = 32),
    size_bytes          BIGINT,
    mimetype            TEXT CHECK (octet_length(mimetype) >= 1)
);

CREATE TABLE IF NOT EXISTS fatcat_file (
    sha1hex             TEXT PRIMARY KEY CHECK (octet_length(sha1hex) = 40),
    file_ident          TEXT CHECK (octet_length(file_ident) = 26),
    first_release_ident TEXT CHECK (octet_length(first_release_ident) = 26)
);

CREATE TABLE IF NOT EXISTS petabox (
    item                TEXT NOT NULL CHECK (octet_length(item) >= 1),
    path                TEXT NOT NULL CHECK (octet_length(path) >= 1),
    sha1hex             TEXT NOT NULL CHECK (octet_length(sha1hex) = 40),
    PRIMARY KEY(item, path)
);
CREATE INDEX petabox_sha1hex_idx ON petabox(sha1hex);

CREATE TABLE IF NOT EXISTS grobid (
    sha1hex             TEXT PRIMARY KEY CHECK (octet_length(sha1hex) = 40),
    updated             TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    grobid_version      TEXT CHECK (octet_length(grobid_version) >= 1),
    status_code         INT NOT NULL,
    status              TEXT CHECK (octet_length(status) >= 1),
    fatcat_release      TEXT CHECK (octet_length(fatcat_release) = 26),
    -- extracted basic biblio metadata:
    --  title
    --  authors[]
    --    full/display
    --    given_name
    --    surname
    --    affiliation
    --  year
    --  journal_issn
    --  journal_name
    --  refs_count
    metadata            JSONB
);
-- CREATE INDEX grobid_fatcat_release_idx ON grobid(fatcat_release);

CREATE TABLE IF NOT EXISTS ingest_request (
    link_source             TEXT NOT NULL CHECK (octet_length(link_source) >= 1),
    link_source_id          TEXT NOT NULL CHECK (octet_length(link_source_id) >= 1),
    ingest_type             TEXT NOT NULL CHECK (octet_length(ingest_type) >= 1),
    base_url                TEXT NOT NULL CHECK (octet_length(base_url) >= 1),

    ingest_request_source   TEXT CHECK (octet_length(ingest_request_source) >= 1),
    created                 TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    release_stage           TEXT CHECK (octet_length(release_stage) >= 1),
    request                 JSONB,
    -- request isn't required, but can stash extra fields there for import, eg:
    --   ext_ids (source/source_id sometimes enough)
    --   fatcat_release (if ext_ids and source/source_id not specific enough; eg SPN)
    --   edit_extra

    PRIMARY KEY (link_source, link_source_id, ingest_type, base_url)
);
CREATE INDEX ingest_request_base_url_idx ON ingest_request(base_url, ingest_type);

CREATE TABLE IF NOT EXISTS ingest_file_result (
    ingest_type             TEXT NOT NULL CHECK (octet_length(ingest_type) >= 1),
    base_url                TEXT NOT NULL CHECK (octet_length(base_url) >= 1),

    updated                 TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    hit                     BOOLEAN NOT NULL,
    status                  TEXT CHECK (octet_length(terminal_url) >= 1),
    terminal_url            TEXT CHECK (octet_length(terminal_url) >= 1),
    terminal_dt             TEXT CHECK (octet_length(terminal_dt) = 14),
    terminal_status_code    INT,
    terminal_sha1hex        TEXT CHECK (octet_length(terminal_sha1hex) = 40),

    PRIMARY KEY (ingest_type, base_url)
);
CREATE INDEX ingest_file_result_terminal_url_idx ON ingest_file_result(terminal_url);
CREATE INDEX ingest_file_result_terminal_sha1hex_idx ON ingest_file_result(terminal_sha1hex);

CREATE TABLE IF NOT EXISTS shadow (
    shadow_corpus       TEXT NOT NULL CHECK (octet_length(shadow_corpus) >= 1),
    shadow_id           TEXT NOT NULL CHECK (octet_length(shadow_id) >= 1),
    sha1hex             TEXT NOT NULL CHECK (octet_length(sha1hex) = 40),
    doi                 TEXT CHECK (octet_length(doi) >= 1),
    pmid                TEXT CHECK (octet_length(pmid) >= 1),
    isbn13              TEXT CHECK (octet_length(isbn13) >= 1),
    PRIMARY KEY(shadow_corpus, shadow_id)
);
CREATE INDEX shadow_sha1hex_idx ON shadow(sha1hex);
