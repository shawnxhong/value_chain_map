FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ARG http_proxy
ARG https_proxy
ARG no_proxy

RUN pip install --proxy "${HTTPS_PROXY}" --no-cache-dir uv

# Install dependencies first (better layer caching), then the package.
COPY pyproject.toml README.md ./
COPY vcm ./vcm
RUN uv pip install --system -e .

# Migrations + Alembic config (applied on startup by the entrypoint).
COPY alembic.ini ./
COPY alembic ./alembic
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

# Runs `alembic upgrade head` then starts uvicorn (see docker-entrypoint.sh).
ENTRYPOINT ["./docker-entrypoint.sh"]
