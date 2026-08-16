"""
Fully transparent reverse proxy to xAI API (https://api.x.ai).

All incoming requests (method, path, query, headers, body) are forwarded
as-is to the upstream. No authentication, no rewriting, no extra logic.
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
TIMEOUT = httpx.Timeout(None)  # no timeout – LLM streams can be long

# Hop-by-hop headers that must not be forwarded
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
}


@asynccontextmanager
async def lifespan(app: Starlette):
    # Shared client with connection pooling + HTTP/2
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

    # Preserve original path + query string exactly
    path = request.url.path
    if request.url.query:
        path = f"{path}?{request.url.query}"

    # Forward headers (strip hop-by-hop)
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in HOP_BY_HOP
    }

    # Stream the request body to upstream (supports large / streaming uploads)
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

    # Response headers: strip hop-by-hop and length/encoding
    # (uvicorn will handle framing correctly)
    resp_headers = {
        k: v
        for k, v in upstream_resp.headers.items()
        if k.lower() not in HOP_BY_HOP
        and k.lower() not in ("content-encoding", "content-length")
    }

    async def response_body() -> AsyncIterator[bytes]:
        try:
            async for chunk in upstream_resp.aiter_raw():
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
        # Catch-all for any path (including root)
        Route("/{path:path}", endpoint=proxy, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]),
        Route("/", endpoint=proxy, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]),
    ],
)
