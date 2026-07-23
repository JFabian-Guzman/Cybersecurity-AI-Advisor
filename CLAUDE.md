# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An AI-powered platform that scans repositories, Dockerfiles, Kubernetes manifests, and IaC for security
misconfigurations and lets users ask natural-language questions about the findings (RAG-grounded, cited
answers). See [README.md](README.md) for the pitch, [DESIGN.md](DESIGN.md) for the full architecture
(components, data flow, DB schema, tech-stack rationale table), and [PLAN.md](PLAN.md) for the sprint-by-sprint
roadmap and current MVP scope. [docs/adr/](docs/adr/) holds architecture decision records — check there before
revisiting a stack or branching decision; add a new ADR for any similarly significant decision.

**Current state**: mid-MVP1 (Sprint 1 territory). The scan pipeline works end-to-end for git-URL repos: connect
a repo → job queued on Redis/RQ → worker clones it, runs the sandboxed Dockerfile analyzer, and persists
findings → frontend polls scan status and renders a findings dashboard. Kubernetes/Terraform analysis, secret
detection, the reporting/export module, embeddings/RAG, the chatbot, and real auth are not built yet — auth is
a single stub user (see "Auth is stubbed" below), and `.zip`/`.tar` upload ingestion is stubbed (accepted and
persisted, but the worker only clones `git_url` repos; see `jobs.py`'s `Unsupported source type` check).

## Commands

### Local dev (full stack)
```bash
cp .env.example .env
docker compose up --build              # postgres, redis, pgadmin, backend, worker, frontend
docker compose --profile sandbox up --build   # also builds/runs the sandbox image standalone
```
- Backend health: `curl http://localhost:8000/api/health`
- DB round trip: `curl http://localhost:8000/api/db-check`
- Frontend: http://localhost:5173
- pgAdmin: http://localhost:5050

### Backend (`backend/`, uv-managed, Python 3.14)
```bash
uv sync --frozen
uv run alembic upgrade head   # apply migrations (needed before first run outside compose)
uv run python seed.py         # creates the stub user other code depends on
uv run ruff check .           # lint
uv run black --check .        # format check (drop --check to auto-format)
uv run mypy .                 # type check
uv run pytest                 # all tests
uv run pytest tests/test_health.py::test_health_returns_ok   # single test
```
Worker (consumes the `scans` RQ queue; requires Docker socket access to spawn sandbox containers):
```bash
uv run python worker.py
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
the backend's 3.14) that runs `sandbox/entrypoint.py` over a repo mounted read-only at `/repo`, printing a JSON
array of findings to stdout. It has no network, no DB, a read-only FS, dropped caps, and resource limits
(`SANDBOX_TIMEOUT_SECONDS`, `SANDBOX_MAX_CLONE_MB`, 512m/1cpu/128 pids — see `docker-compose.yml` and ADR
[0002](docs/adr/0002-sandbox-isolation-mechanism.md)). The worker (`jobs.py::_run_sandbox`) spawns one ephemeral
container per scan via the `docker` SDK and removes it after reading the result.

### Pre-commit
`.pre-commit-config.yaml` runs gitleaks, ruff (`--fix`), and black. CI (`.github/workflows/ci.yml`) separately
runs backend lint/format/mypy/pytest, frontend lint/format/typecheck/build, and a full-history gitleaks scan on
every PR into `develop`/`main` and every branch push.

## Architecture notes

- **Backend is one FastAPI app** (`backend/main.py`) intended to serve both the web (API) and worker roles from
  the same image per the ADR — `worker.py` is a separate entrypoint/process (see the `worker` service in
  `docker-compose.yml`) but shares the same codebase and image build as the API.
- **Scan pipeline**: `routers/repositories.py` creates a `Repository` + queued `Scan` row and enqueues
  `jobs.run_scan` on the `scans` RQ queue (`worker.py::get_queue`). `jobs.run_scan` clones the repo
  (`ingestion/clone.py`, shallow, hook-neutralized, size/time-limited), runs it through the sandbox container,
  maps the returned findings' severities (`_SEVERITY_MAP`), and persists `Finding` rows — all inside one
  try/except that flips `Scan.status` through `queued → running → succeeded|failed`.
- **`backend/db.py`** owns the only DB engine; `_normalized_database_url()` rewrites `postgresql://`/`postgres://`
  URLs to `postgresql+psycopg://` because Render's connection string doesn't include the driver. Reuse this
  pattern if more DB-touching code is added — don't create a second engine.
- **Schema/migrations**: SQLAlchemy models live in `backend/models.py` (`User → Repository → Scan → Finding`,
  all UUID-keyed and owner-scoped via `user_id`). Alembic migrations are in `backend/alembic/versions/`; generate
  new ones with `uv run alembic revision --autogenerate -m "..."` after model changes, then `alembic upgrade head`.
- **Auth is stubbed**: `dependencies.py::get_current_user` always resolves to a hardcoded `STUB_USER_ID`, created
  by `seed.py`. Every router still threads `current_user` through queries (e.g. `scans.py::_get_owned_scan`
  filters by `user_id`) so the owner-scoping pattern is already in place for when real auth lands — follow it
  for any new endpoint rather than querying unscoped.
- **Ingestion vs. Analysis split**: `ingestion/` (runs in the worker, outside the sandbox) only clones and
  classifies files (`classify.py::inspect_repo` — file-type/project-type detection, not used by the scan
  pipeline yet). `analysis/` (runs *inside* the sandbox via `sandbox/entrypoint.py`) contains the actual
  detector logic — currently `analysis/docker.py`'s five Dockerfile checks (DF001–DF005, see
  [fixtures/README.md](fixtures/README.md) for the rule catalogue and golden-dataset fixtures used to validate
  them). New detectors (Kubernetes, Terraform, secrets) should follow this split and live in `analysis/`.
- **Security boundary**: any code that parses or executes content from a user-supplied repository must run in
  the sandbox container, never in the main backend/worker process — this is the core invariant DESIGN.md is
  built around (no network/DB access from the sandbox, structured findings only flow back out via stdout JSON).
- **Frontend** uses TanStack Query for server state and Axios (`frontend/src/lib/api-client.ts`) as the HTTP
  client; `VITE_API_URL` env var points at the backend, defaulting to `http://localhost:8000`. Feature code is
  organized under `frontend/src/features/` (`api/` — query/mutation hooks per endpoint, `components/`, `types/`);
  `frontend/src/components/ui/` holds shadcn/ui primitives (Tailwind v4, see `components.json`). `App.tsx` drives
  a simple two-state flow: connect-a-repo form vs. poll-and-render scan status/findings, keyed off a `scanId`
  query param.
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
