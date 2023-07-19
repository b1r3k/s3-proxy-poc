import asyncio

import boto3

from .http_client import AsyncHttpClient
from .logging import root_logger

logger = root_logger.getChild(__name__)


def get_credentials_for_role(role_arn):
    sts_client = boto3.client("sts")
    response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName="s3proxy")

    # Retrieve the temporary credentials
    credentials = response["Credentials"]

    # Create a new session using the assumed role's credentials
    # assumed_session = boto3.Session(
    #     aws_access_key_id=credentials['AccessKeyId'],
    #     aws_secret_access_key=credentials['SecretAccessKey'],
    #     aws_session_token=credentials['SessionToken']
    # )
    # ec2_client = assumed_session.client('ec2')
    return (
        credentials["AccessKeyId"],
        credentials["SecretAccessKey"],
        credentials["SessionToken"],
        credentials["Expiration"],
    )


class AwsAccessProvider:
    def __init__(self, access_key=None, secret_key=None):
        if access_key is not None and secret_key is not None:
            root_logger.info("Using provided AWS credentials instead of IAM role")
        self._access_key = access_key
        self._secret_key = secret_key
        self._role_arn = None
        self._invalidation_callback = None
        self._http_client = AsyncHttpClient()

    async def get_role_arn(self):
        if self._role_arn is None:
            self._role_arn = await self.get_iam_role_arn()
        return self._role_arn

    async def get_access_secret_key(self):
        if self._access_key is None or self._secret_key is None:
            await self.refresh_access_key()
        return self._access_key, self._secret_key

    async def close(self):
        await self._http_client.close_session()

    async def get_iam_role_arn(self):
        iam_url = "http://169.254.169.254/latest/dynamic/instance-identity/document"
        response = await self._http_client.request("get", iam_url)
        identity_document = response.json()
        return identity_document["instanceProfileArn"]

    async def invalidate_access_key(self):
        self._access_key = None
        self._secret_key = None
        self._invalidation_callback = None

    async def refresh_access_key(self):
        loop = asyncio.get_event_loop()
        role_arn = await self.get_role_arn()
        access_key, access_secret, session_token, expiration = get_credentials_for_role(role_arn)
        if self._invalidation_callback is not None:
            self._invalidation_callback.cancel()
        self._invalidation_callback = loop.call_at(expiration.timestamp(), self.invalidate_access_key)
        self._access_key = access_key
        self._secret_key = access_secret
