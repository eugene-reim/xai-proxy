# xAI Transparent Proxy

Полностью прозрачный reverse-proxy к API xAI (`https://api.x.ai`).

Никакой дополнительной логики: авторизация, rate-limit, логирование запросов, модификация заголовков/тела — отсутствуют.  
Всё, что приходит на этот сервис, уходит на `api.x.ai` один-в-один (метод, путь, query, headers, body).

## Быстрый старт

### Docker

```bash
docker build -t xai-proxy .
docker run --rm -p 8080:8080 xai-proxy
```

Теперь можно обращаться к `http://localhost:8080/v1/...` вместо `https://api.x.ai/v1/...`.

Пример:

```bash
curl http://localhost:8080/v1/models \
  -H "Authorization: Bearer $XAI_API_KEY"
```

### Переопределение upstream

```bash
docker run --rm -p 8080:8080 -e UPSTREAM_URL=https://eu-west-1.api.x.ai xai-proxy
```

### Локально (с uv)

```bash
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8080
```

## Архитектура

- **Python 3.12** + **uv** + **Starlette** + **httpx** (HTTP/2)
- Полная поддержка streaming (SSE / chunked) — критично для LLM
- Multi-stage Dockerfile → минимальный runtime-образ
- Non-root user внутри контейнера
- GitHub Actions workflow собирает multi-arch образ (`linux/amd64`, `linux/arm64`) и пушит в GHCR

## Файлы проекта

```
├── main.py                 # сам прокси
├── pyproject.toml          # зависимости (uv)
├── uv.lock
├── Dockerfile              # multi-stage
├── .dockerignore
├── .gitignore
├── .github/workflows/docker.yml
└── README.md
```

## Почему Python + uv, а не nginx?

Для LLM-прокси (особенно streaming) разница в latency между nginx и httpx+uvicorn практически незаметна — узкое место всегда модель.  
При этом Python-решение проще кастомизировать в будущем, если понадобится (хотя сейчас функционал намеренно нулевой).
