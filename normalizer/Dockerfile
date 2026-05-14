FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

FROM base AS deps

COPY pyproject.toml uv.lock* ./
COPY shared/ ./shared/
COPY normalizer/pyproject.toml ./normalizer/

RUN uv sync --no-dev

FROM base AS runtime

COPY --from=deps /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY shared/ ./shared/
COPY normalizer/ ./normalizer/

EXPOSE 8000

CMD ["litestar", "--app", "normalizer.app.main:app", "run", "--host", "0.0.0.0", "--port", "8000"]
