
from datetime import datetime

NORMAL_MIME = (
    'application/pdf',
    'application/postscript',
    'text/html',
    'text/xml',
)

def normalize_mime(raw):
    raw = raw.lower()
    for norm in NORMAL_MIME:
        if raw.startswith(norm):
            return norm

    # Special cases
    if raw.startswith('application/xml'):
        return 'text/xml'
    if raw.startswith('application/x-pdf'):
        return 'application/pdf'
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


def parse_cdx_line(raw_cdx):

    cdx = raw_cdx.split()
    if len(cdx) < 11:
        return None

    surt = cdx[0]
    dt = cdx[1]
    url = cdx[2]
    mime = normalize_mime(cdx[3])
    http_status = cdx[4]
    key = cdx[5]
    c_size = cdx[8]
    offset = cdx[9]
    warc = cdx[10]

    if not (key.isalnum() and c_size.isdigit() and offset.isdigit()
            and http_status == "200" and len(key) == 32 and dt.isdigit()
            and mime != None):
        return None

    if '-' in (surt, dt, url, mime, http_status, key, c_size, offset, warc):
        return None

    key = "sha1:{}".format(key)

    info = dict(surt=surt, dt=dt, url=url, c_size=int(c_size),
        offset=int(offset), warc=warc)

    warc_file = warc.split('/')[-1]
    try:
        dt_iso = datetime.strptime(dt, "%Y%m%d%H%M%S").isoformat()
    except Exception:
        return None

    # 'i' intentionally not set
    heritrix = dict(u=url, d=dt_iso, f=warc_file, o=int(offset), c=1)
    return {'key': key, 'file:mime': mime, 'file:cdx': info, 'f:c': heritrix}
