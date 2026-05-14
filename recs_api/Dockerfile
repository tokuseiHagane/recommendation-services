FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY uv-bin /bin/uv

FROM base AS deps

COPY pyproject.toml uv.lock* ./
COPY shared/ ./shared/
COPY recs_api/pyproject.toml ./recs_api/

RUN uv sync --no-dev

FROM base AS runtime

COPY --from=deps /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY shared/ ./shared/
COPY recs_api/ ./recs_api/

EXPOSE 8000

CMD ["litestar", "--app", "recs_api.app.main:app", "run", "--host", "0.0.0.0", "--port", "8000"]
