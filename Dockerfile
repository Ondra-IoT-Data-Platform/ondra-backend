# STAGE 1: Builder
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*


COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /usr/local/bin/uv

ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_PYTHON_DOWNLOADS=never


COPY pyproject.toml uv.lock ./


RUN uv sync --frozen --no-dev

# STAGE 2: Runtime
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment built in stage 1
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY . .


EXPOSE 8001

# Uvicorn runs Django as an ASGI app — required for Django Ninja async support.
# --host 0.0.0.0 means the container accepts traffic from outside itself.
CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
