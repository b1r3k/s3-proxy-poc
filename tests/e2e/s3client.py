import logging
from os import environ

import boto3

log_level = environ.get("LOG_LEVEL", "INFO")

logger = logging.getLogger()
logger.setLevel(level=logging.getLevelName(log_level))

if log_level == "DEBUG":
    boto3.set_stream_logger(name="botocore")


def get_boto_client(endpoint_url, aws_access_key_id, aws_secret_access_key):
    logger.info("Creating boto client with endpoint_url=%s", endpoint_url)
    logger.info("AWS_ACCESS_KEY_ID=%s", aws_access_key_id)
    logger.info("AWS_SECRET_ACCESS_KEY=%s", aws_secret_access_key)
    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=None,
        endpoint_url=endpoint_url,
        config=boto3.session.Config(signature_version="s3v4", retries={"max_attempts": 0}),
    )
    return s3
