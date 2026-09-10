# /bin/sh
# STAGE 1: Builder
FROM python:3.13.3-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ENV UV_HTTP_TIMEOUT=300

ENV MPLCONFIGDIR=/tmp/matplotlib


WORKDIR /app

RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /tmp/matplotlib

COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /usr/local/bin/uv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

# STAGE 2: Runtime
FROM python:3.13.3-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

ENV UV_HTTP_TIMEOUT=300

ENV MPLCONFIGDIR=/tmp/matplotlib


WORKDIR /app

RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment built in stage 1
COPY --from=builder /opt/venv /opt/venv
RUN ls -la /opt/venv/bin/ || echo "venv missing"

RUN mkdir -p /tmp/matplotlib
# Copy application source code
COPY app/ .

COPY app/entrypoint.sh /entrypoint.sh

RUN chown -R 1000:1000 /app \
    && chmod +x /entrypoint.sh

EXPOSE 8001

ENTRYPOINT ["/entrypoint.sh"]
