
import io
import os
import hashlib

import minio


class SandcrawlerMinioClient(object):

    def __init__(self, host_url, access_key, secret_key, default_bucket=None):
        """
        host is minio connection string (host:port)
        access and secret key are as expected
        default_bucket can be supplied so that it doesn't need to be repeated for each function call

        Example config:

            host="localhost:9000",
            access_key=os.environ['MINIO_ACCESS_KEY'],
            secret_key=os.environ['MINIO_SECRET_KEY'],
        """
        self.mc = minio.Minio(
            host_url,
            access_key=access_key,
            secret_key=secret_key,
            secure=False,
        )
        self.default_bucket = default_bucket

    def _blob_path(self, folder, sha1hex: str, extension: str, prefix):
        if not extension:
            extension = ""
        if not prefix:
            prefix = ""
        assert len(sha1hex) == 40
        obj_path = "{}{}/{}/{}/{}{}".format(
            prefix,
            folder,
            sha1hex[0:2],
            sha1hex[2:4],
            sha1hex,
            extension,
        )
        return obj_path

    def put_blob(self, folder, blob, sha1hex=None, extension="", prefix="", bucket=None):
        """
        blob should be bytes
        sha1hex is assumed to be sha1 of the blob itself; if not supplied it will be calculated
        Uploads blob to path in the given bucket. Files are stored in a top-level
        folder, then in two levels of sub-directory based on sha1, then the
        filename is SHA1 with an optional file extension.
        """
        if type(blob) == str:
            blob = blob.encode('utf-8')
        assert type(blob) == bytes
        if not sha1hex:
            h = hashlib.sha1()
            h.update(blob)
            sha1hex = h.hexdigest()
        obj_path = self._blob_path(folder, sha1hex, extension, prefix)
        if not bucket:
            bucket = self.default_bucket
        assert bucket
        content_type = "application/octet-stream"
        if extension.endswith('.xml'):
            content_type = "application/xml"
        self.mc.put_object(
            bucket,
            obj_path,
            io.BytesIO(blob),
            len(blob),
            content_type=content_type,
        )
        return (bucket, obj_path)

    def get_blob(self, folder, sha1hex, extension="", prefix="", bucket=None):
        """
        sha1hex is sha1 of the blob itself

        Fetched blob from the given bucket/folder, using the sandcrawler SHA1 path convention
        """
        obj_path = self._blob_path(folder, sha1hex, extension, prefix)
        if not bucket:
            bucket = self.default_bucket
        assert bucket
        blob = self.mc.get_object(
            bucket,
            obj_path,
        )
        # TODO: optionally verify SHA-1?
        return blob
