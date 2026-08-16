# xAI Transparent Proxy

Fully transparent reverse proxy to the xAI API (`https://api.x.ai`).

No auth, rate limiting, logging, or request/response rewriting.  
Every request is forwarded as-is (method, path, query, headers, body).

## Quick start

### Docker

```bash
docker build -t xai-proxy .
docker run --rm -p 8080:8080 xai-proxy
```

Point your client to `http://localhost:8080` instead of `https://api.x.ai`.

```bash
curl http://localhost:8080/v1/models \
  -H "Authorization: Bearer $XAI_API_KEY"
```

### Custom upstream

```bash
docker run --rm -p 8080:8080 -e UPSTREAM_URL=https://eu-west-1.api.x.ai xai-proxy
```

### Local (uv)

```bash
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8080
```

## Stack

- Python 3.12 + uv + Starlette + httpx (HTTP/2)
- Full streaming support (SSE / chunked)
- Multi-stage Dockerfile, non-root runtime
- GitHub Actions: multi-arch image (`amd64`/`arm64`) pushed to GHCR
