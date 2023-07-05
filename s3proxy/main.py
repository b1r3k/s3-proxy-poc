import time

import httpx
from starlette.applications import Starlette
from starlette.datastructures import URL
from starlette.responses import Response, StreamingResponse
from starlette.routing import Route

from .aws import AwsAccessProvider
from .awssigv4 import get_v4_signature
from .config import settings
from .http_client import AsyncHttpClient
from .logging import root_logger

http_client = None
aws_access_provider: AwsAccessProvider | None = None


def get_signed_headers(headers):
    """
    Extracts the signed headers from the authorization header.
    AWS4-HMAC-SHA256 Credential=XXX/20230604/us-east-1/s3/aws4_request,
    SignedHeaders=host;x-amz-content-sha256;x-amz-date,
    Signature=f28f713e944a460459192579f386c5e5831c882bd0ec670500bc6eda68af3bdf

    :param headers:
    :return:
    """
    try:
        auth_parts = headers["authorization"].split(",")
        # print("auth_parts: ", auth_parts)
        signed_headers = auth_parts[1].split("=")[1]
        # host;x-amz-content-sha256;x-amz-date
        signed_headers = [header_name for header_name in signed_headers.split(";")]
        # [host, x-amz-content-sha256, x-amz-date]
        return signed_headers
    except KeyError:
        return []


async def get_proxied_response(aws_provider: AwsAccessProvider, client, incoming_req):
    # Extract the target URL from the request
    # target_host = "s3.us-east-1.amazonaws.com"
    target_url = URL(settings.AWS_S3_ENDPOINT_URL)
    target_url = incoming_req.url.replace(hostname=target_url.hostname, scheme=target_url.scheme, port=target_url.port)
    root_logger.debug("Forwarding to: " + str(target_url))
    # Create a new request to the target server
    headers = {k: v for k, v in incoming_req.headers.items()}
    endpoint = target_url.hostname
    headers["host"] = endpoint
    signed_headers_names = get_signed_headers(headers)
    if len(signed_headers_names):
        signed_headers = {k: v for k, v in headers.items() if k.lower() in signed_headers_names}
        access_key, secret_key = await aws_provider.get_access_secret_key()
        new_signature = get_v4_signature(
            access_key,
            secret_key,
            endpoint,
            "us-east-1",
            "s3",
            incoming_req.method,
            incoming_req.url.path,
            signed_headers,
            params=incoming_req.query_params,
            body_hash=headers.get("x-amz-content-sha256"),
        )
        headers["authorization"] = new_signature
        # otherwise this is unsigned request or presigned url, and so we don't need to do anything
        # presigned urls need to be created for specific host which is going to be used for download
        # boto3 will use endpoint url for presigned url host therefore presigned url will be invalid if used with proxy
        # such request could be rewritten to use endpoint host instead of proxy host just as authorization header does
    has_content = int(headers.get("content-length", 0)) > 0
    data = incoming_req.stream() if has_content else None
    # If there is something broken it may be beneficial to read the body here and check the hash but production code
    # should always stream body to the target server
    # body = b''
    # async for chunk in incoming_req.stream():
    #     body += chunk
    # print('Body SHA256: %s' % hashlib.sha256(body).hexdigest())
    proxy_request = client.build_request(incoming_req.method, str(target_url), headers=headers, data=data)
    response = await client.send(proxy_request)
    return response


async def handle(request):
    global aws_access_provider

    # Perform the request to the target server
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await get_proxied_response(aws_access_provider, client, request)
        # Create a streaming response to send back to the client
        proxy_response = StreamingResponse(
            response.aiter_bytes(), status_code=response.status_code, headers=response.headers
        )
        return proxy_response


async def healthcheck(request):
    return Response(f"OK {time.time()}", status_code=200)


async def app_startup():
    global http_client
    global aws_access_provider

    root_logger.info("Starting up..")
    http_client = AsyncHttpClient()
    aws_access_provider = AwsAccessProvider(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)


async def app_shutdown():
    global http_client
    global aws_access_provider

    root_logger.info("Shutting down..")

    if http_client:
        await http_client.close_session()
    if aws_access_provider:
        await aws_access_provider.close()


def app_factory():
    allowed_methods = ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"]

    app = Starlette(
        debug=settings.DEBUG,
        routes=[
            Route("/", handle, methods=allowed_methods),
            Route("/healthcheck", healthcheck, methods=["GET"]),
            Route("/{path:path}", handle, methods=allowed_methods),
        ],
        on_startup=[app_startup],
        on_shutdown=[app_shutdown],
    )
    return app
