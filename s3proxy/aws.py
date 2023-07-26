import asyncio
import os
from datetime import datetime

import boto3
import httpx

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

    def get_iam_host(self):
        # AWS_CONTAINER_CREDENTIALS_RELATIVE_URI is available only in fargate
        # see: [Task IAM role - Amazon Elastic Container Service]
        # (https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html)
        iam_cred_rel_uri = os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
        if iam_cred_rel_uri is not None:
            return "http://169.254.170.2"
        return "http://169.254.169.254"

    def get_iam_cred_uri(self):
        iam_cred_rel_uri = os.environ.get(
            "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI", "/latest/meta-data/iam/security-credentials/"
        )
        return iam_cred_rel_uri

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
        iam_host = self.get_iam_host()
        iam_url = f"{iam_host}/latest/dynamic/instance-identity/document"
        try:
            response = await self._http_client.request("get", iam_url)
            response.raise_for_status()
            identity_document = response.json()
            return identity_document["instanceProfileArn"]
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 400:
                raise Exception(f"Failed to get instance identity document from {iam_url}")
            else:
                raise exc

    async def get_credentials(self):
        iam_host = self.get_iam_host()
        iam_cred_uri = self.get_iam_cred_uri()
        iam_url = f"{iam_host}{iam_cred_uri}"
        response = await self._http_client.request("get", iam_url)
        response.raise_for_status()
        credentials = response.json()
        return (
            credentials["AccessKeyId"],
            credentials["SecretAccessKey"],
            credentials.get("SessionToken") or credentials.get("Token"),
            credentials.get("Expiration"),
        )

    async def invalidate_access_key(self):
        self._access_key = None
        self._secret_key = None
        self._invalidation_callback = None

    async def refresh_access_key(self):
        loop = asyncio.get_event_loop()
        try:
            role_arn = await self.get_role_arn()
            access_key, access_secret, session_token, expiration_date = get_credentials_for_role(role_arn)
        except Exception as e:
            logger.warning("Failed to get role arn, performing fallback", exc_info=e)
            access_key, access_secret, session_token, expiration_date = await self.get_credentials()
        if self._invalidation_callback is not None:
            self._invalidation_callback.cancel()
        # expiration date and time format: 2023-07-26T22:16:38Z
        expiration_dt = datetime.strptime(expiration_date, "%Y-%m-%dT%H:%M:%SZ")
        expiration_tm = expiration_dt.timestamp()
        self._invalidation_callback = loop.call_at(int(expiration_tm), self.invalidate_access_key)
        self._access_key = access_key
        self._secret_key = access_secret
