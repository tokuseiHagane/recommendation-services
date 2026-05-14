# syntax=docker/dockerfile:1.7
# =============================================================================
# Stage 1: Builder — uv + CPython 3.14 уже в образе.
# apt не вызываем вообще: все зависимости (asyncpg, cryptography, hiredis)
# имеют готовые cp314 manylinux wheels на PyPI.
# =============================================================================
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS builder

ARG BUILD_ENV=dev

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

# Ставим только зависимости — слой переиспользуется до тех пор,
# пока не меняются pyproject.toml / uv.lock.
# Bind-mount вместо COPY: кэш не инвалидируется от метаданных файлов.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    if [ "$BUILD_ENV" = "dev" ]; then \
        uv sync --locked --no-install-project --extra dev; \
    else \
        uv sync --locked --no-install-project --no-dev; \
    fi

# =============================================================================
# Stage 2: Runtime — чистый python slim без apt-слоёв.
# asyncpg реализует протокол PostgreSQL сам, libpq в рантайме не нужна.
# =============================================================================
FROM python:3.14-slim-trixie AS runtime

WORKDIR /app

ARG BUILD_ENV=dev

RUN useradd --create-home --shell /bin/bash appuser

COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY pyproject.toml .
COPY piccolo_conf.py .

RUN mkdir -p /app/data \
    && chown -R appuser:appuser /app \
    && chmod +x /app/scripts/entrypoint.sh

USER appuser

LABEL build.env="${BUILD_ENV}"

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
