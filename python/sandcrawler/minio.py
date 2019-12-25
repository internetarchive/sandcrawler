
import os
import minio


class SandcrawlerMinioClient(object):

    def __init__(self, host, access_key, secret_key, default_bucket=None):
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
            host,
            access_key=access_key,
            secret_key=secret_key,
            secure=False,
        )
        self.default_bucket = default_bucket

    def upload_blob(self, folder, blob, sha1hex=None, extension="", prefix="", bucket=None):
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
        obj_path = "{}{}/{}/{}/{}{}".format(
            prefix,
            folder,
            sha1hex[0:2],
            sha1hex[2:4],
            sha1hex,
            extension,
        )
        if not bucket:
            bucket = self.default_bucket
        self.mc.put_object(
            self.default_bucket,
            obj_path,
            blob,
            len(blob),
        )
        return (bucket, obj_path)
