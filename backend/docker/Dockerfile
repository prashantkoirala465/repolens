# Multi-stage, multi-target: `api` and `worker` share the same dependency layer
# and only differ in entrypoint, matching the pattern used across this
# portfolio's other Go/Python services (one image, target-selected process).
FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
RUN uv sync --no-dev

FROM base AS api
EXPOSE 8000
# --no-sync: dependencies are already installed by the `uv sync --no-dev` build
# steps above. Without it, `uv run` re-syncs to the full lockfile — including
# the dev group (ruff/mypy) — on every container start, defeating the point
# of the --no-dev build.
CMD ["uv", "run", "--no-sync", "uvicorn", "repolens.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS worker
CMD ["uv", "run", "--no-sync", "arq", "repolens.workers.settings.WorkerSettings"]

FROM base AS migrate
CMD ["uv", "run", "--no-sync", "alembic", "upgrade", "head"]
