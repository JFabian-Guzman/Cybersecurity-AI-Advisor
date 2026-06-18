## Components

### Frontend
The client-facing application that **users interact with**. It **communicates exclusively with the Web Process** through the API, and is responsible for displaying scan results, reports, and Q&A responses.

---
### Web Process
The public-facing process that **handles all incoming requests**. It manages authentication, exposes the API endpoints, enqueues background jobs, and serves data reads such as reports and chat history. 

---
### Worker Process
Runs in the background, **consuming jobs from the Message Queue and driving the scan pipeline**. It coordinates the flow between Ingestion, Analysis, Persistence, and the Sandbox. Multiple instances can run in parallel to scale throughput.

---
### Auth / Identity
Owns everything related to users, sessions, and login. Other modules rely on it to **verify who is making a request and whether they have permission** to access a given resource. Ownership rules are enforced here.

---
### Ingestion
Responsible for **accepting repositories** — either via file upload or a remote URL — and preparing them for analysis. It detects project type, lists files, and delegates untrusted content to the Sandbox. It never directly touches repo bytes itself.

---
### Analysis
Contains the detector plugin framework. Each security check (secrets, misconfigurations, vulnerabilities) is a self-contained plugin registered into a registry and run over the Sandbox's output. Detectors are independent of each other, making it easy to add new checks incrementally.

---
### Reporting
**Aggregates findings produced by the Analysis module into structured reports**. Handles severity grouping, PDF/Markdown export, and diff comparisons between scan runs. It is read-only over findings — it composes and formats, but does not detect.

---
### Persistence
The only module that talks directly to the database. It **exposes clean data-access interfaces** (e.g. "save findings", "fetch chunks") to the rest of the system. All queries are scoped to the owning user, preventing any data from leaking across tenants.

---
### Jobs / Queue
**Owns the job queue and the worker entrypoint**. It sequences a full scan job — Ingestion → Sandbox → Analysis → Persistence → embed — and conducts the flow without holding any business logic itself.

---
### Assistant
**Handles the AI-powered Q&A feature**. It chunks and embeds repository content, performs similarity searches, assembles prompts, calls the AI provider, and returns cited answers. It is the only module that communicates with the external AI provider, and it treats all retrieved content as untrusted data.

---
### Sandbox — Isolated
A deliberately separate, **locked-down execution environment**. It is the only place where **untrusted repository content is handled**. It has no access to the database or the network, runs under strict CPU, time, and size limits, and returns only structured findings back to the application. This is what makes the security boundary real.

---
### Database
The system's source of truth. **Stores repositories, scan runs, findings, file chunks, and embeddings.** The vector search capability allows the Assistant to perform similarity-based retrieval for Q&A. All data is scoped per user.

---
### Message Queue
Acts as the communication channel between the Web Process and the Worker Process. **When a scan is triggered, a job is placed in the queue and picked up asynchronously by a worker**, decoupling request handling from long-running scan execution.

---
### AI Provider
**An external service that generates natural language responses**. It is called exclusively by the Assistant module and receives only structured, sanitized prompts — never raw repository content directly.
## Data flow

#### Upload data 
```mermaid
flowchart TD
  A[Browser uploads / connects a repo] --> B[API enqueues scan job]
  B --> C[(Redis: pending scan jobs)]
  C --> D[Worker pulls and runs job]
  D --> E[[Sandbox: clone, parse, run detectors]]
  E --> F[(PostgreSQL: findings, owner-scoped)]
  F --> G[(pgvector: chunk + embed for RAG)]
```

#### Request data

```mermaid
flowchart TD
  A[Browser asks a security question] --> B[API embeds question and retrieves]
  B --> C[(pgvector returns relevant chunks)]
  C --> D[LLM answers from retrieved context]
  D --> E[Browser renders cited answer]
```
## Schema

```mermaid

erDiagram

    users ||--o{ repositories : owns

    users ||--o{ conversations : starts

    repositories ||--o{ scan_runs : "has"

    repositories ||--o{ conversations : "about"

    scan_runs ||--o{ findings : produces

    scan_runs ||--o{ chunks : "indexes into"

    conversations ||--o{ messages : contains

    messages ||--o{ citations : cites

    chunks ||--o{ citations : "cited by"

  

    users {

        uuid id PK

        text email UK

        text hashed_password

    }

    repositories {

        uuid id PK

        uuid user_id FK

        text name

        text source_type "upload | git_url"

        text source_ref "url or storage key"

    }

    scan_runs {

        uuid id PK

        uuid repository_id FK

        text status "queued | running | completed | failed"

        text error "nullable"

        timestamptz started_at "nullable"

        timestamptz finished_at "nullable"

    }

    findings {

        uuid id PK

        uuid scan_run_id FK

        text category "docker | kubernetes | secret"

        text severity "high | medium | low"

        text title

        text description

        text file_path

        int line_number "nullable"

        text remediation

    }

    chunks {

        uuid id PK

        uuid scan_run_id FK

        text source_path

        text content

        int chunk_index

        int token_count

        vector embedding "pgvector, e.g. 1536-dim"

    }

    conversations {

        uuid id PK

        uuid user_id FK

        uuid repository_id FK

        text title

    }

    messages {

        uuid id PK

        uuid conversation_id FK

        text role "user | assistant"

        text content

    }

    citations {

        uuid id PK

        uuid message_id FK

        uuid chunk_id FK

        text source_path "file/section snapshot"

        float score "similarity"

    }

```

## Tech Stack

| Architectural driver                                                                                    | Tech                                                                             |
| ------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| One image for web+worker, RAG-dominant                                                                  | **Python 3.12+**                                                                 |
| Stateless API tier validating *adversarial* input, needs OpenAPI                                        | **FastAPI** (alt: Litestar)                                                      |
| System of record + owner-scoping + vectors + delete-on-request must purge findings, chunks & embeddings | **PostgreSQL + pgvector**                                                        |
| Long scans must not block HTTP; rate-limit/quota store needed                                           | **Redis + RQ** (or arq)                                                          |
| Evolving owner-scoped schema                                                                            | **SQLAlchemy 2.0 + Alembic**                                                     |
| Per-scan isolation of untrusted bytes (no net, no DB, caps, ephemeral FS)                               | **Ephemeral hardened OCI container** per scan                                    |
| RAG: embeddings, retrieval, citations, untrusted context                                                | **Provider-agnostic LLM interface + pgvector retrieval + local Ollama option**   |
| Frontend = pure API client, auth-gated (no SEO)                                                         | **React + Vite + React Router + TanStack Query**, TS strict                      |
| Repo init / build                                                                                       | **uv** (Python), **pnpm** (JS), multi-stage **Docker**, **docker-compose** local |
| Source + automation                                                                                     | **GitHub + GitHub Actions**                                                      |
| Observability across web→queue→worker→sandbox                                                           | **structlog + correlation IDs + Sentry** (optional OpenTelemetry)                |