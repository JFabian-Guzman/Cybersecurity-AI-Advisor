# 0001. Technology stack and branching strategy

- Status: accepted
- Date: 2026-06-22
- Deciders: Project team

## Context

We are building an AI-powered platform that scans repositories and infrastructure for
security risks and answers natural-language questions about them. The system must run
untrusted repository content safely, store owner-scoped data including vector
embeddings, perform long-running scans without blocking HTTP, and be operable by a
small part-time team. We need an agreed stack and a branching model before development
starts so the decision is traceable and onboarding is fast.

## Decision

We will use the following stack:

- Backend language: Python 3.14, managed with uv. The sandbox image intentionally
  pins Python 3.12 because it is a separate, locked-down build with its own lifecycle.
- API: FastAPI, serving a stateless, OpenAPI-documented JSON API that validates
  adversarial input.
- Data store: PostgreSQL with the pgvector extension, as the single system of record
  for repositories, scan runs, findings, chunks, and embeddings, all owner-scoped.
- Background work: Redis with RQ, so long scans run as jobs off the request path.
- Schema management: SQLAlchemy 2.0 with Alembic migrations.
- Untrusted execution: an ephemeral, hardened OCI container per scan, with no network
  or database access and strict CPU, time, and size limits.
- AI layer: a provider-agnostic LLM interface over pgvector retrieval, with a local
  Ollama option, treating all retrieved repository content as untrusted.
- Frontend: React with Vite, React Router, and TanStack Query, in TypeScript strict
  mode, as a pure auth-gated API client.
- Tooling: uv (Python), pnpm (JavaScript), multi-stage Docker with docker-compose for
  local development, GitHub with GitHub Actions for CI/CD.
- Observability: structlog with correlation IDs and Sentry.

We will use a GitFlow branching model:

- `main` is always deployable and tagged at each sprint end (e.g. `v0.1.0`).
- `develop` is the integration branch.
- `feature/<short-description>` and `fix/<short-description>` branch off `develop`.
- Commits follow Conventional Commits; every PR must pass CI (lint, tests, secret
  scan) and be reviewed before merge.
- At sprint end, `develop` merges to `main`, the release is tagged, and the tagged
  commit deploys to the live environment.

## Consequences

### Positive

- One language and one image cover both the web and worker tiers, simplifying builds.
- pgvector keeps relational data and embeddings in a single store, easing owner-scoped
  deletion across findings, chunks, and embeddings.
- A separate sandbox image makes the security boundary explicit and independently
  upgradable.
- GitFlow plus required CI gives a predictable, reviewable path from feature to deploy.

### Negative

- Python 3.14 is recent; some libraries may lag, and the sandbox/backend version split
  must be kept documented to avoid confusion.
- GitFlow adds branch overhead that a two-person team must keep disciplined about,
  mitigated by the 48-hour self-merge rule already in CONTRIBUTING.

## Alternatives considered

- Litestar instead of FastAPI: viable, but FastAPI's ecosystem and OpenAPI maturity
  win for a team optimizing for learning and speed.
- A dedicated vector database (e.g. Qdrant) instead of pgvector: rejected to avoid a
  second data store and to keep owner-scoped deletes atomic.
- Trunk-based development instead of GitFlow: rejected because sprint-tagged releases
  and explicit review gates suit a part-time, portfolio-focused team better.
