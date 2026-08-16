"""
Fully transparent reverse proxy to xAI API (https://api.x.ai).

Forwards method, path, query, headers and body as-is.
No authentication, rewriting or extra logic.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import StreamingResponse
from starlette.routing import Route

UPSTREAM_BASE = os.getenv("UPSTREAM_URL", "https://api.x.ai").rstrip("/")
TIMEOUT = httpx.Timeout(None)

# Request headers that must not be forwarded
REQUEST_SKIP = {
    "host",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-length",  # httpx recalculates
}

# Response headers that must not be forwarded
RESPONSE_SKIP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-encoding",  # we decompress via aiter_bytes()
    "content-length",    # length changes after decompress / streaming
    "server",
    "date",
    "set-cookie",
    "strict-transport-security",
    "cf-ray",
    "cf-cache-status",
    "cf-apo-via",
    "alt-svc",
}


@asynccontextmanager
async def lifespan(app: Starlette):
    app.state.client = httpx.AsyncClient(
        base_url=UPSTREAM_BASE,
        timeout=TIMEOUT,
        follow_redirects=False,
        http2=True,
    )
    yield
    await app.state.client.aclose()


async def proxy(request: Request) -> StreamingResponse:
    client: httpx.AsyncClient = request.app.state.client

    path = request.url.path
    if request.url.query:
        path = f"{path}?{request.url.query}"

    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in REQUEST_SKIP
    }

    async def request_body() -> AsyncIterator[bytes]:
        async for chunk in request.stream():
            yield chunk

    method = request.method
    content = request_body() if method not in ("GET", "HEAD", "OPTIONS") else None

    upstream_req = client.build_request(
        method=method,
        url=path,
        headers=headers,
        content=content,
    )

    upstream_resp = await client.send(upstream_req, stream=True)

    resp_headers = {
        k: v
        for k, v in upstream_resp.headers.items()
        if k.lower() not in RESPONSE_SKIP
    }

    # aiter_bytes() decompresses gzip/br; aiter_raw() would leave compressed body
    async def response_body() -> AsyncIterator[bytes]:
        try:
            async for chunk in upstream_resp.aiter_bytes():
                yield chunk
        finally:
            await upstream_resp.aclose()

    return StreamingResponse(
        content=response_body(),
        status_code=upstream_resp.status_code,
        headers=resp_headers,
    )


app = Starlette(
    lifespan=lifespan,
    routes=[
        Route("/{path:path}", endpoint=proxy, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]),
        Route("/", endpoint=proxy, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]),
    ],
)
