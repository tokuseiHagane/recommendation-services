FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

FROM base AS deps

COPY pyproject.toml uv.lock* ./
COPY shared/ ./shared/
COPY indexer/pyproject.toml ./indexer/

RUN uv sync --no-dev

FROM base AS runtime

COPY --from=deps /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY shared/ ./shared/
COPY indexer/ ./indexer/

EXPOSE 8000

CMD ["opentelemetry-instrument", "litestar", "--app", "indexer.app.main:app", "run", "--host", "0.0.0.0", "--port", "8000"]
