
import os
import base64
import magic
import hashlib
import datetime
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry # pylint: disable=import-error
import urlcanon


def clean_url(s: str) -> str:
    s = s.strip()
    parsed = urlcanon.parse_url(s)
    if not parsed.port and parsed.colon_before_port:
        parsed.colon_before_port = b''
    return str(urlcanon.whatwg(parsed))

def url_fuzzy_equal(left: str, right: str) -> bool:
    """
    TODO: use proper surt library and canonicalization for this check
    """
    fuzzy_left = '://'.join(clean_url(left).replace('www.', '').replace(':80/', '/').split('://')[1:])
    fuzzy_right = '://'.join(clean_url(right).replace('www.', '').replace(':80/', '/').split('://')[1:])
    if fuzzy_left == fuzzy_right:
        return True
    elif fuzzy_left == fuzzy_right + "/" or fuzzy_right == fuzzy_left + "/":
        return True
    return False

def test_url_fuzzy_equal() -> None:
    assert True == url_fuzzy_equal(
        "http://www.annalsofian.org/article.asp?issn=0972-2327;year=2014;volume=17;issue=4;spage=463;epage=465;aulast=Nithyashree",
        "http://annalsofian.org/article.asp?issn=0972-2327;year=2014;volume=17;issue=4;spage=463;epage=465;aulast=Nithyashree")

def gen_file_metadata(blob: bytes, allow_empty: bool = False) -> dict:
    """
    Takes a file blob (bytestream) and returns hashes and other metadata.

    Returns a dict: size_bytes, md5hex, sha1hex, sha256hex, mimetype
    """
    assert blob is not None
    if not allow_empty:
        assert blob
    if len(blob) < 1024*1024:
        mimetype = magic.Magic(mime=True).from_buffer(blob)
    else:
        mimetype = magic.Magic(mime=True).from_buffer(blob[:(1024*1024)])
    if mimetype in ("application/xml", "text/xml"):
        # crude checks for XHTML or JATS XML, using only first 1 kB of file
        if b"<htm" in blob[:1024] and b'xmlns="http://www.w3.org/1999/xhtml"' in blob[:1024]:
            mimetype = "application/xhtml+xml"
        elif b"<article " in blob[:1024] and not b"<html" in blob[:1024]:
            mimetype = "application/jats+xml"
    hashes = [
        hashlib.sha1(),
        hashlib.sha256(),
        hashlib.md5(),
    ]
    for h in hashes:
        h.update(blob)
    return dict(
        size_bytes=len(blob),
        sha1hex=hashes[0].hexdigest(),
        sha256hex=hashes[1].hexdigest(),
        md5hex=hashes[2].hexdigest(),
        mimetype=mimetype,
    )

def gen_file_metadata_path(path: str, allow_empty: bool = False) -> dict:
    """
    Variant of gen_file_metadata() which works with files on local disk
    """
    assert path is not None
    mimetype = magic.Magic(mime=True).from_file(path)
    if mimetype in ("application/xml", "text/xml"):
        with open(path, 'rb') as f:
            blob = f.read(1024)
            # crude checks for XHTML or JATS XML, using only first 1 kB of file
            if b"<htm" in blob[:1024] and b'xmlns="http://www.w3.org/1999/xhtml"' in blob[:1024]:
                mimetype = "application/xhtml+xml"
            elif b"<article " in blob[:1024] and not b"<html" in blob[:1024]:
                mimetype = "application/jats+xml"
    hashes = [
        hashlib.sha1(),
        hashlib.sha256(),
        hashlib.md5(),
    ]
    size_bytes = 0
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(1024*1024)
            if not chunk:
                break
            size_bytes += len(chunk)
            for h in hashes:
                h.update(chunk)
    if not allow_empty:
        assert size_bytes > 0
    return dict(
        size_bytes=size_bytes,
        sha1hex=hashes[0].hexdigest(),
        sha256hex=hashes[1].hexdigest(),
        md5hex=hashes[2].hexdigest(),
        mimetype=mimetype,
    )

def b32_hex(s: str) -> str:
    """
    Converts a base32-encoded SHA-1 checksum into hex-encoded

    base32 checksums are used by, eg, heritrix and in wayback CDX files
    """
    s = s.strip().split()[0].lower()
    if s.startswith("sha1:"):
        s = s[5:]
    if len(s) != 32:
        if len(s) == 40:
            return s
        raise ValueError("not a base-32 encoded SHA-1 hash: {}".format(s))
    return base64.b16encode(base64.b32decode(s.upper())).lower().decode('utf-8')

NORMAL_MIME = (
    'application/pdf',
    'application/postscript',
    'text/html',
    'text/xml',
    'application/octet-stream',
)

def normalize_mime(raw: str) -> Optional[str]:
    raw = raw.lower().strip()
    for norm in NORMAL_MIME:
        if raw.startswith(norm):
            return norm

    # Special cases
    if raw.startswith('application/xml'):
        return 'text/xml'
    if raw.startswith('application/x-pdf'):
        return 'application/pdf'
    if raw in (
            '.pdf',
            ):
        return 'application/pdf'
    if raw in (
            'application/download',
            'binary/octet-stream',
            'unk',
            'application/x-download',
            'application/octetstream',
            'application/force-download',
            'application/unknown',
            ):
        return 'application/octet-stream'
    return None


def test_normalize_mime():
    assert normalize_mime("asdf") is None
    assert normalize_mime("application/pdf") == "application/pdf"
    assert normalize_mime("application/pdf+journal") == "application/pdf"
    assert normalize_mime("Application/PDF") == "application/pdf"
    assert normalize_mime("application/p") is None
    assert normalize_mime("application/xml+stuff") == "text/xml"
    assert normalize_mime("application/x-pdf") == "application/pdf"
    assert normalize_mime("application/x-html") is None
    assert normalize_mime("unk") == "application/octet-stream"
    assert normalize_mime("binary/octet-stream") == "application/octet-stream"


def parse_cdx_line(raw_cdx: str, normalize=True) -> Optional[dict]:
    """
    This method always filters a few things out:

    - non-HTTP requests, based on lack of status code (eg, whois)
    """

    cdx = raw_cdx.split()
    if len(cdx) < 11:
        return None

    surt = cdx[0]
    dt = cdx[1]
    url = cdx[2]
    mime = normalize_mime(cdx[3])
    http_status = cdx[4]
    sha1b32 = cdx[5]
    c_size = cdx[8]
    offset = cdx[9]
    warc = cdx[10]

    if not (sha1b32.isalnum() and c_size.isdigit() and offset.isdigit()
            and len(sha1b32) == 32 and dt.isdigit()):
        return None

    if '-' in (surt, dt, url, http_status, sha1b32, c_size, offset, warc):
        return None

    if mime is None or mime == '-':
        mime = "application/octet-stream"

    if normalize:
        mime = normalize_mime(mime)

    sha1hex = b32_hex(sha1b32)

    return dict(
        surt=surt,
        url=url,
        datetime=dt,
        mimetype=mime,
        http_status=int(http_status),
        sha1b32=sha1b32,
        sha1hex=sha1hex,
        warc_csize=int(c_size),
        warc_offset=int(offset),
        warc_path=warc,
    )

def parse_cdx_datetime(dt_str: str) -> Optional[datetime.datetime]:
    if not dt_str:
        return None
    try:
        return datetime.datetime.strptime(dt_str, "%Y%m%d%H%M%S")
    except Exception:
        return None

def test_parse_cdx_datetime() -> None:
    assert parse_cdx_datetime("") == None
    assert parse_cdx_datetime("asdf") == None
    assert parse_cdx_datetime("19930203123045") != None
    assert parse_cdx_datetime("20201028235103") == datetime.datetime(year=2020, month=10, day=28, hour=23, minute=51, second=3)

def datetime_to_cdx(dt: datetime.datetime) -> str:
    return '%04d%02d%02d%02d%02d%02d' % (
        dt.year, dt.month, dt.day,
        dt.hour, dt.minute, dt.second,
    )

def test_datetime_to_cdx() -> None:
    assert "20201028235103" == datetime_to_cdx(datetime.datetime(year=2020, month=10, day=28, hour=23, minute=51, second=3))

def requests_retry_session(retries=10, backoff_factor=3,
        status_forcelist=(500, 502, 504), session=None) -> requests.Session:
    """
    From: https://www.peterbe.com/plog/best-practice-with-retries-with-requests
    """
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def sanitize_fs_path(path: str) -> str:
    """
    From: https://stackoverflow.com/questions/13939120/sanitizing-a-file-path-in-python/66950540#66950540
    """
    # - pretending to chroot to the current directory
    # - cancelling all redundant paths (/.. = /)
    # - making the path relative
    return os.path.relpath(os.path.normpath(os.path.join("/", path)), "/")

def test_sanitize_fs_path() -> None:
    assert sanitize_fs_path("/thing.png") == "thing.png"
    assert sanitize_fs_path("../../thing.png") == "thing.png"
    assert sanitize_fs_path("thing.png") == "thing.png"
    assert sanitize_fs_path("subdir/thing.png") == "subdir/thing.png"
