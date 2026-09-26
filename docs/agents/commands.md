# Commands

## Local dev (full stack)

```bash
docker compose up --build              # postgres, redis, pgadmin, backend, worker, frontend
docker compose --profile sandbox up --build   # also builds/runs the sandbox image standalone
```

## Backend (`backend/`, uv-managed, Python 3.14)

```bash
uv sync --frozen
uv run alembic upgrade head        # apply migrations (needed before first run outside compose)
uv run python -m app.db.seed       # creates the stub user other code depends on
uv run ruff check .                # lint
uv run black --check .             # format check (drop --check to auto-format)
uv run mypy .                      # type check
uv run pytest                      # all tests
uv run pytest tests/test_health.py::test_health_returns_ok   # single test
```

Worker (consumes the `scans` RQ queue; requires Docker socket access to spawn sandbox containers):

```bash
uv run python -m app.worker
```

`poe dev` / `poe worker` / `poe test` wrap the equivalent commands (see `[tool.poe.tasks]` in
`backend/pyproject.toml`); `poe worker` also wraps the worker in `watchfiles` for auto-reload.

## Frontend (`frontend/`, pnpm, React 19 + Vite + TS strict)

```bash
pnpm install --frozen-lockfile
pnpm dev          # vite dev server
pnpm lint
pnpm format:check
pnpm typecheck    # tsc -b
pnpm build
```

