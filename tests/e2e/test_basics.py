import hashlib
import logging
import tempfile
from os import environ, urandom
from unittest import TestCase

from boto3.s3.transfer import TransferConfig

from .s3client import get_boto_client

endpoint_url = environ.get("S3PROXY_ENDPOINT_URL", "http://localhost:8000")
aws_access_key_id = environ.get("AWS_ACCESS_KEY_ID")
aws_secret_access_key = environ.get("AWS_SECRET_ACCESS_KEY")
log_level = environ.get("LOG_LEVEL", "INFO")

logger = logging.getLogger()
logger.setLevel(level=logging.getLevelName(log_level))


class TestBasicAPICalls(TestCase):
    def setUp(self) -> None:
        self.s3 = get_boto_client(endpoint_url, aws_access_key_id, aws_secret_access_key)
        self.bucket_name = "end-to-end.test.bucket"

    def test_list_bucket(self):
        response = self.s3.list_buckets()
        self.assertEqual(response["ResponseMetadata"]["HTTPStatusCode"], 200)

    def test_create_bucket_and_upload_file(self):
        object_size = 1024 * 5
        self.s3.create_bucket(Bucket=self.bucket_name)
        with tempfile.TemporaryFile() as fp:
            # read random bytes and write to file
            data = urandom(object_size)
            md5 = hashlib.md5(data).hexdigest()
            fp.write(data)
            fp.seek(0)
            self.s3.upload_fileobj(fp, self.bucket_name, md5)
        objects = self.s3.list_objects(Bucket=self.bucket_name)
        objects_by_md5 = {obj["ETag"].strip('"'): obj["Size"] for obj in objects["Contents"]}
        self.assertEqual(md5 in objects_by_md5, True, f"object {md5} not found in {objects}")
        self.assertEqual(objects_by_md5[md5], object_size, f"object size mismatch {objects_by_md5[md5]}")

    def test_multipart_upload(self):
        # enable multipart upload for files larger than 6MB
        upload_config = TransferConfig(multipart_threshold=6 * 1024**2)
        # 5 chunks of 6MB each
        object_size = 1024**2 * 6 * 5
        self.s3.create_bucket(Bucket=self.bucket_name)
        with tempfile.TemporaryFile() as fp:
            data = urandom(object_size)
            md5 = hashlib.md5(data).hexdigest()
            fp.write(data)
            fp.seek(0)
            self.s3.upload_fileobj(fp, self.bucket_name, md5, Config=upload_config)
        objects = self.s3.list_objects(Bucket=self.bucket_name)
        objects_by_md5 = {obj["Key"].strip('"'): obj["Size"] for obj in objects["Contents"]}
        self.assertEqual(md5 in objects_by_md5, True, f"object {md5} not found in {objects}")
        self.assertEqual(objects_by_md5[md5], object_size, f"object size mismatch {objects_by_md5[md5]}")

    def test_url_presign_for_download(self):
        object_size = 1024 * 5
        self.s3.create_bucket(Bucket=self.bucket_name)
        with tempfile.TemporaryFile() as fp:
            data = urandom(object_size)
            md5 = hashlib.md5(data).hexdigest()
            fp.write(data)
            fp.seek(0)
            self.s3.upload_fileobj(fp, self.bucket_name, md5)
        self.s3.generate_presigned_url(ClientMethod="get_object", Params={"Bucket": self.bucket_name, "Key": md5})
        # presigning url will work but please note that the url will contain host from endpoint_url which will not
        # work since host points proxy and then proxy will forward request to s3 server which will reject the request
        # with 403 forbidden error
