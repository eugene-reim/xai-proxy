# xAI gRPC Proxy

Transparent **gRPC** reverse proxy to `api.x.ai:443`.

Built for Home Assistant integrations that use the official **xai-sdk** (gRPC), e.g. [pajeronda/xai_conversation](https://github.com/pajeronda/xai_conversation), when direct access to `api.x.ai` is blocked.

Traffic path:

```
HA / xai-sdk  →  :50051 (plaintext gRPC)  →  Envoy  →  TLS  →  api.x.ai:443
```

Designed to run behind [Gluetun](https://github.com/qdm12/gluetun) so upstream goes through VPN.

## Quick start

```bash
docker build -t xai-proxy .
docker run --rm -p 50051:50051 xai-proxy
```

With Gluetun — see `docker-compose.yml`.

## Home Assistant (pajeronda/xai_conversation)

The xAI SDK uses a **secure** gRPC channel by default. Pointing it at this proxy requires plaintext (insecure) mode.

### 1. Proxy address

| Setup | `api_host` value |
|-------|------------------|
| HA on same host, port published | `localhost:50051` |
| HA elsewhere on LAN | `192.168.x.x:50051` |

`localhost:50051` is special-cased by xai-sdk (local credentials, no TLS).  
For a LAN IP you must enable insecure channel (patch below).

### 2. Patch `xai_gateway.py` (one-time)

In `custom_components/xai_conversation/xai_gateway.py`, where the client is created, add `use_insecure_channel=True` when using the proxy:

```python
client_kwargs = {
    "api_key": api_key,
    "timeout": timeout,
    "channel_options": self._get_channel_options(),
    "use_insecure_channel": True,  # required for this proxy
}
api_host = self.entry.data.get(CONF_API_HOST, DEFAULT_API_HOST)
if api_host:
    client_kwargs["api_host"] = api_host
```

Do the same in `create_client_from_api_key` / `async_validate_api_key` if they pass `api_host`.

### 3. Integration config

Set **API host** to your proxy, e.g.:

```text
192.168.1.100:50051
```

or `localhost:50051` if HA shares the host.

API key stays your real xAI key (`xai-...`). Auth is forwarded in gRPC metadata.

## Gluetun

```bash
docker compose up -d --build
```

Port `50051` is published on the **gluetun** container (`network_mode: service:gluetun`).

## Ports

| Port | Purpose |
|------|---------|
| `50051` | gRPC (client → proxy) |
| `9901`  | Envoy admin (localhost inside container only) |

## Notes

- Not an HTTP/OpenAI-compatible proxy. For REST clients use a separate HTTP proxy.
- Upstream is always `api.x.ai:443` with SNI. Override only by editing `envoy.yaml`.
- Long-lived streams: timeouts disabled so LLM/tool calls are not cut off.
