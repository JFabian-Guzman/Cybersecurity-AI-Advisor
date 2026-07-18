# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An AI-powered platform that scans repositories, Dockerfiles, Kubernetes manifests, and IaC for security
misconfigurations and lets users ask natural-language questions about the findings (RAG-grounded, cited
answers). See [README.md](README.md) for the pitch, [DESIGN.md](DESIGN.md) for the full architecture
(components, data flow, DB schema, tech-stack rationale table), and [PLAN.md](PLAN.md) for the sprint-by-sprint
roadmap and current MVP scope. [docs/adr/](docs/adr/) holds architecture decision records — check there before
revisiting a stack or branching decision; add a new ADR for any similarly significant decision.

**Current state**: walking-skeleton stage only (frontend → backend → Postgres round trip deployed to Render).
None of the ingestion/sandbox/analysis/RAG pipeline described in DESIGN.md and PLAN.md exists yet — `backend/db.py`
and `backend/main.py` are the entire backend, and `backend/sandbox/Dockerfile` is an unwired stub.

## Commands

### Local dev (full stack)
```bash
cp .env.example .env
docker compose up --build
```
- Backend health: `curl http://localhost:8000/api/health`
- DB round trip: `curl http://localhost:8000/api/db-check`
- Frontend: http://localhost:5173

### Backend (`backend/`, uv-managed, Python 3.14)
```bash
uv sync --frozen
uv run ruff check .          # lint
uv run black --check .       # format check (drop --check to auto-format)
uv run mypy .                # type check
uv run pytest                # all tests
uv run pytest tests/test_health.py::test_health_returns_ok   # single test
```

### Frontend (`frontend/`, pnpm, React 19 + Vite + TS strict)
```bash
pnpm install --frozen-lockfile
pnpm dev          # vite dev server
pnpm lint
pnpm format:check
pnpm typecheck    # tsc -b
pnpm build
```

### Sandbox image
`backend/sandbox/Dockerfile` builds a separate, locked-down Python 3.12 image (intentionally pinned apart from
the backend's 3.14) for running untrusted repo content. Build/run it via the `sandbox` docker-compose profile
(`docker compose --profile sandbox up`); it has no network, no DB, read-only FS, dropped caps, and resource limits.

### Pre-commit
`.pre-commit-config.yaml` runs gitleaks, ruff (`--fix`), and black. CI (`.github/workflows/ci.yml`) separately
runs backend lint/format/mypy/pytest, frontend lint/format/typecheck/build, and a full-history gitleaks scan on
every PR into `develop`/`main` and every branch push.

## Architecture notes

- **Backend is one FastAPI app** (`backend/main.py`) intended to serve both the web (API) and worker roles from
  the same image per the ADR — there's no separate worker entrypoint yet.
- **`backend/db.py`** owns the only DB engine; `_normalized_database_url()` rewrites `postgresql://`/`postgres://`
  URLs to `postgresql+psycopg://` because Render's connection string doesn't include the driver. Reuse this
  pattern if more DB-touching code is added — don't create a second engine.
- **Persistence is meant to be the sole DB access layer** per DESIGN.md once it exists — other modules (ingestion,
  analysis, assistant) should go through it rather than querying directly, to keep owner-scoping centralized.
- **Security boundary**: any code that parses or executes content from a user-supplied repository must run in
  the sandbox container, never in the main backend process — this is the core invariant DESIGN.md is built
  around (no network/DB access from the sandbox, structured findings only flow back out).
- **Frontend is a pure API client** (no SEO concerns) — TanStack Query for server state (see `App.tsx`'s
  `useQuery` usage), `frontend/src/api.ts` is the thin fetch wrapper per backend endpoint. `VITE_API_URL` env var
  points at the backend; defaults to `http://localhost:8000`.
- **Deploy**: tagging `v*` triggers `.github/workflows/deploy.yml`, which POSTs to Render deploy hooks for the
  backend and frontend services defined in `render.yaml` (both `autoDeploy: false`, so only tag pushes deploy).

## Conventions (from CONTRIBUTING.md)

- Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`).
- snake_case for variables/functions, camelCase for filenames.
- 120-char line limit (enforced by ruff/black on the backend).
- GitFlow: `main` (tagged releases) ← `develop` (integration) ← `feature/<desc>` / `fix/<desc>`. PRs target
  `develop`; CI must pass; self-merge allowed after 48h without review.

## Default versions

- Default React version: 19.2.6
- Default Python version: 3.14
