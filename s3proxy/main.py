import logging

import httpx
from starlette.applications import Starlette
from starlette.responses import StreamingResponse
from starlette.routing import Route

from .awssigv4 import get_v4_signature
from .config import settings

logger = logging.getLogger()
logger.setLevel(level=logging.getLevelName(settings.LOG_LEVEL))


def get_signed_headers(headers):
    """
    Extracts the signed headers from the authorization header.
    AWS4-HMAC-SHA256 Credential=XXX/20230604/us-east-1/s3/aws4_request,
    SignedHeaders=host;x-amz-content-sha256;x-amz-date,
    Signature=f28f713e944a460459192579f386c5e5831c882bd0ec670500bc6eda68af3bdf

    :param headers:
    :return:
    """
    auth_parts = headers["authorization"].split(",")
    # print("auth_parts: ", auth_parts)
    signed_headers = auth_parts[1].split("=")[1]
    # host;x-amz-content-sha256;x-amz-date
    signed_headers = [header_name for header_name in signed_headers.split(";")]
    # [host, x-amz-content-sha256, x-amz-date]
    return signed_headers


async def get_proxied_response(client, incoming_req):
    # Extract the target URL from the request
    target_host = "s3.us-east-1.amazonaws.com"
    target_url = incoming_req.url.replace(hostname=target_host, scheme="https", port=443)
    logger.debug("Forwarding to: " + str(target_url))
    # Create a new request to the target server
    headers = {k: v for k, v in incoming_req.headers.items()}
    endpoint = target_url.hostname
    headers["host"] = endpoint
    signed_headers_names = get_signed_headers(headers)
    signed_headers = {k: v for k, v in headers.items() if k.lower() in signed_headers_names}
    new_signature = get_v4_signature(
        settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY,
        endpoint,
        "us-east-1",
        "s3",
        incoming_req.method,
        incoming_req.url.path,
        signed_headers,
        body_hash=headers.get("x-amz-content-sha256"),
    )

    headers["authorization"] = new_signature
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
    # print('Proxy request: %s' % str(proxy_request))
    # print('Proxy request headers: %s' % str(proxy_request.headers.raw))
    return response


async def handle(request):
    # Perform the request to the target server
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await get_proxied_response(client, request)
        # Create a streaming response to send back to the client
        proxy_response = StreamingResponse(response.aiter_bytes(), status_code=response.status_code)

        return proxy_response


def app_factory():
    allowed_methods = ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"]
    app = Starlette(
        debug=settings.DEBUG,
        routes=[Route("/", handle, methods=allowed_methods), Route("/{path:path}", handle, methods=allowed_methods)],
    )
    return app
