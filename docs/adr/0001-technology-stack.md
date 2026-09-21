# 0001. Technology stack

- Status: accepted
- Date: 2026-06-22
- Deciders: Fabián Guzmán, Andrés Víquez

## Context

We are building an AI-powered platform that scans repositories and infrastructure for
security risks and answers natural-language questions about them. The system must run
untrusted repository content safely, store owner-scoped data including vector
embeddings, perform long-running scans without blocking HTTP, and be operable by a
small part-time team. We need an agreed stack before development starts so the decision
is traceable and onboarding is fast. The branching model is recorded separately in
[0004](0004-branching-strategy.md).

## Decision

We will use the following stack. Items marked **(planned)** are decided but not yet
implemented.

- Backend language: Python 3.14, managed with uv. The sandbox image intentionally
  pins Python 3.12 because it is a separate, locked-down build with its own lifecycle.
- API: FastAPI, serving a stateless, OpenAPI-documented JSON API that validates
  adversarial input.
- Data store: PostgreSQL with the pgvector extension, as the single system of record
  for repositories, scan runs, findings, chunks, and embeddings, all owner-scoped.
- Background work: Redis with RQ, so long scans run as jobs off the request path.
- Schema management: SQLAlchemy 2.0 with Alembic migrations.
- Untrusted execution: an ephemeral, hardened OCI container per scan, with no network
  or database access and strict CPU, time, and size limits. See
  [0002](0002-sandbox-isolation-mechanism.md).
- AI layer **(planned)**: a provider-agnostic LLM interface over pgvector retrieval,
  with a local Ollama option, treating all retrieved repository content as untrusted.
- Frontend: React with Vite, React Router, and TanStack Query, in TypeScript strict
  mode, as a pure auth-gated API client.
- Tooling: uv (Python), pnpm (JavaScript), multi-stage Docker with docker-compose for
  local development, GitHub with GitHub Actions for CI/CD.
- Observability: structlog with correlation IDs, plus Sentry **(planned)**.

## Consequences

### Positive

- One language and one image cover both the web and worker tiers, simplifying builds.
- pgvector keeps relational data and embeddings in a single store, easing owner-scoped
  deletion across findings, chunks, and embeddings.
- A separate sandbox image makes the security boundary explicit and independently
  upgradable.

### Negative

- Python 3.14 is recent; some libraries may lag, and the sandbox/backend version split
  must be kept documented to avoid confusion.
