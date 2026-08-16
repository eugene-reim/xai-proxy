# syntax=docker/dockerfile:1

# ── Stage 1: dependency builder with uv ──────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Enable bytecode compilation and copy mode for better Docker layer caching
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install dependencies only (we run main.py directly, no need to install the project)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev --frozen

# Application source
COPY main.py ./

# ── Stage 2: minimal runtime image ───────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Create non-root user
RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --no-create-home app

# Copy the virtual environment from builder
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/main.py /app/main.py

# Make venv the default Python
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER app

EXPOSE 8080

# Default upstream can be overridden at runtime
ENV UPSTREAM_URL=https://api.x.ai

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
