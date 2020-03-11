
import base64
import magic
import hashlib
import datetime
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry # pylint: disable=import-error
import urlcanon


def clean_url(s):
    parsed = urlcanon.parse_url(s)
    if not parsed.port and parsed.colon_before_port:
        parsed.colon_before_port = b''
    return str(urlcanon.whatwg(parsed))

def gen_file_metadata(blob):
    """
    Takes a file blob (bytestream) and returns hashes and other metadata.

    Returns a dict: size_bytes, md5hex, sha1hex, sha256hex, mimetype
    """
    assert blob
    mimetype = magic.Magic(mime=True).from_buffer(blob)
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

def b32_hex(s):
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

def normalize_mime(raw):
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


def parse_cdx_line(raw_cdx, normalize=True):
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
    http_status = int(http_status)
    c_size = int(c_size)
    offset = int(offset)

    return dict(
        surt=surt,
        url=url,
        datetime=dt,
        mimetype=mime,
        http_status=http_status,
        sha1b32=sha1b32,
        sha1hex=sha1hex,
        warc_csize=c_size,
        warc_offset=offset,
        warc_path=warc,
    )

def parse_cdx_datetime(dt_str):
    try:
        return datetime.strptime(dt_str, "%Y%m%d%H%M%S")
    except Exception:
        return None


def requests_retry_session(retries=10, backoff_factor=3,
        status_forcelist=(500, 502, 504), session=None):
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

