import httpx
from starlette.applications import Starlette
from starlette.responses import StreamingResponse
from starlette.routing import Route


async def handle(request):
    # Extract the target URL from the request
    target_url = httpx.URL("https://www.onet.pl")

    # Create a new request to the target server
    headers = {k: v for k, v in request.headers.items()}
    headers["host"] = target_url.host
    proxy_request = httpx.Request(method=request.method, url=target_url, headers=headers)

    # Perform the request to the target server
    async with httpx.AsyncClient() as client:
        # print(proxy_request)
        # print(proxy_request.headers)
        response = await client.send(proxy_request)
        # print(response)
        # Create a streaming response to send back to the client
        proxy_response = StreamingResponse(response.iter_bytes(), status_code=response.status_code)
        for key, value in response.headers.items():
            proxy_response.headers[key] = value
        # print(proxy_response.headers)

        return proxy_response


app = Starlette(routes=[Route("/", handle), Route("/{path:path}", handle)])
