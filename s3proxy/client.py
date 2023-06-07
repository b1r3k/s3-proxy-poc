import argparse
import logging

import boto3

from .config import settings

logger = logging.getLogger()
logger.setLevel(level=logging.getLevelName(settings.LOG_LEVEL))

if settings.LOG_LEVEL == "DEBUG":
    boto3.set_stream_logger(name="botocore")


def get_boto_client(application_key_id, application_key):
    s3 = boto3.client(
        "s3",
        endpoint_url="http://localhost:8000",
        config=boto3.session.Config(
            signature_version="v4", region_name="us-east-1", retries={"max_attempts": 1, "mode": "standard"}
        ),
    )
    return s3


def cli():
    parser = argparse.ArgumentParser(description="Backblaze B2 CLI")
    parser.add_argument("--key-id", help="Application Key ID", default=settings.B2_APP_KEY_ID)
    parser.add_argument("--key", help="Application Key", default=settings.B2_APP_KEY)
    parser.add_argument("--bucket", help="Bucket Name", default=None)
    parser.add_argument("--file", help="File to upload")
    args = parser.parse_args()
    if args.key_id is None or args.key is None:
        raise ValueError("You must specify a key and key id")

    s3 = get_boto_client(args.key_id, args.key)
    response = s3.list_buckets()

    # Output the bucket names
    print("Existing buckets:")
    for bucket in response["Buckets"]:
        print(f'  {bucket["Name"]}')
    if args.bucket:
        print(f"Uploading {args.file} to {args.bucket}")
        with open(args.file, "rb") as fd:
            s3.upload_fileobj(fd, args.bucket, args.file)
