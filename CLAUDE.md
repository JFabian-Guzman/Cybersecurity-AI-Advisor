# CLAUDE.md

AI-powered platform that scans repos, Dockerfiles, Kubernetes manifests, and IaC for security misconfigurations
and answers natural-language questions about the findings (RAG-grounded, cited).

- Package managers: **uv** (backend, `backend/`), **pnpm** (frontend, `frontend/`)

## Read when relevant

Only open a document when its condition applies; don't read them all up front.

- [Commands](docs/agents/commands.md): read before running, building, testing, or linting anything (local dev stack,
  backend/frontend/sandbox commands, pre-commit, CI), or when a command fails unexpectedly
- [Conventions](CONTRIBUTING.md): read before writing or reviewing code, naming things, creating a branch, committing,
  or opening a PR
- [DESIGN.md](docs/design/DESIGN.md): read when a task crosses module boundaries or touches the scan pipeline, the
  sandbox boundary, or the Q&A flow
- [SCHEMA.md](docs/design/SCHEMA.md): read when adding or changing models, migrations, or queries. The models and
  Alembic migrations are authoritative for what exists today; this is the target schema
- [THEME.md](docs/design/THEME.md): read only when building or changing frontend UI or styling
- [PLAN.md](docs/planning/PLAN.md): read when asked what to build next, what is in scope for the MVP, or which sprint
  something belongs to (per-sprint detail is in `docs/planning/sprints/`)
- [ADRs](docs/adr/README.md): read the ones that touch the area you are about to change, especially before proposing a
  change to the stack, the sandbox, chunking, or the branching model
- [Deployment](docs/DEPLOYMENT.md): read only for Render, `render.yaml`, environment variables, or release/deploy tasks
- [Detector rules and fixtures](fixtures/README.md): read when adding or changing a detector rule, or writing tests
  that use the fixture repos
