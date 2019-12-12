
-- file_meta: more NOT NULL
CREATE TABLE IF NOT EXISTS file_meta (
    sha1hex             TEXT NOT NULL PRIMARY KEY CHECK (octet_length(sha1hex) = 40),
    sha256hex           TEXT NOT NULL CHECK (octet_length(sha256hex) = 64),
    md5hex              TEXT NOT NULL CHECK (octet_length(md5hex) = 32),
    size_bytes          BIGINT NOT NULL,
    mimetype            TEXT CHECK (octet_length(mimetype) >= 1)
);

-- CDX: add domain/host columns?
CREATE TABLE IF NOT EXISTS cdx (
    url                 TEXT NOT NULL CHECK (octet_length(url) >= 1),
    datetime            TEXT NOT NULL CHECK (octet_length(datetime) = 14),
    sha1hex             TEXT NOT NULL CHECK (octet_length(sha1hex) = 40),
    cdx_sha1hex         TEXT CHECK (octet_length(cdx_sha1hex) = 40),
    mimetype            TEXT CHECK (octet_length(mimetype) >= 1),
    warc_path           TEXT CHECK (octet_length(warc_path) >= 1),
    warc_csize          BIGINT,
    warc_offset         BIGINT,
    row_created         TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    domain              TEXT NOT NULL CHECK (octet_length(domain) >= 1),
    host                TEXT NOT NULL CHECK (octet_length(host) >= 1),
    PRIMARY KEY(url, datetime)
);
CREATE INDEX IF NOT EXISTS cdx_sha1hex_idx ON cdx(sha1hex);
CREATE INDEX IF NOT EXISTS cdx_row_created_idx ON cdx(row_created);

-- direct fast import with just md5hex; big UPDATE via join with file_meta
CREATE TABLE IF NOT EXISTS shadow (
    shadow_corpus       TEXT NOT NULL CHECK (octet_length(shadow_corpus) >= 1),
    shadow_id           TEXT NOT NULL CHECK (octet_length(shadow_id) >= 1),
    sha1hex             TEXT CHECK (octet_length(sha1hex) = 40),
    md5hex              TEXT CHECK (octet_length(md5hex) = 32),
    doi                 TEXT CHECK (octet_length(doi) >= 1),
    pmid                TEXT CHECK (octet_length(pmid) >= 1),
    isbn13              TEXT CHECK (octet_length(isbn13) >= 1),
    PRIMARY KEY(shadow_corpus, shadow_id)
);
CREATE INDEX shadow_sha1hex_idx ON shadow(sha1hex);
