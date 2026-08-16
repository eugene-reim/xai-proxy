# syntax=docker/dockerfile:1

# ── Stage 1: dependency builder with uv ──────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_INDEX_URL=https://pypi.org/simple

# Only pyproject.toml — resolve fresh from official PyPI (avoids bad lockfile registries)
COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev

COPY main.py ./

# ── Stage 2: minimal runtime image ───────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

RUN groupadd --system --gid 999 app \
    && useradd --system --uid 999 --gid app --no-create-home app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/main.py /app/main.py

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER app

EXPOSE 8080

ENV UPSTREAM_URL=https://api.x.ai

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
