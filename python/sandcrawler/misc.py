
import base64
import magic
import hashlib

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

