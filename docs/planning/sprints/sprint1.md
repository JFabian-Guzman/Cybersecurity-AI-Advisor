# Sprint 1 — Repository Ingestion, Sandboxing & Dockerfile Analysis

**Splitting principle:** the seam is *"produces a repo-on-disk path"* (Dev A) vs *"consumes a
repo-on-disk path"* (Dev B). Dev B's analysis engine is a pure library testable offline against
the golden dataset, so the two streams run in parallel with a single integration point at the end
of the sprint (Dev A's worker calls Dev B's `analyze()` with a real cloned path instead of a
fixture path).

> **Convention:** every record that is persisted carries a non-null `user_id` FK from day one
> (stub user, pre-login). This is repeated in the acceptance criteria of every story that writes
> data, on purpose — to prevent tenant-filter omissions later.

---

## Shared kickoff (do first — commit to `develop` before either dev branches)

These are the only true cross-dev dependencies. Freeze them in one session:

1. **Full schema, all four tables** (`User`, `Repository`, `Scan`, `Finding`) with `user_id` FK on
   each. Decided jointly; **Dev A writes one initial Alembic migration** containing all four tables
   (kills linear-history conflicts — Dev B never touches migrations this sprint).
2. **Detector interface + `Finding` shape:** `analyze(repo_path: Path) -> list[Finding]`. Dev A's
   worker imports it; until Dev B ships, Dev A wires a stub returning `[]`.
3. **API route map:** Dev A owns `/api/repositories` + `/api/scans`; Dev B owns
   `/api/scans/{id}/findings`.
4. **Golden-dataset fixture layout** so Dev A can grab one repo to smoke-test the clone pipeline.

---

## Dev A — Ingestion Pipeline & Platform

### S1.1 — Connect / upload a repository
> **As a** user, **I want** to upload an archive or connect a public Git repository by URL, **so
> that** the system can clone and store it for analysis.

**Acceptance criteria**
- `POST /api/repositories` accepts either a public Git HTTPS URL or an uploaded archive (zip/tarball).
- A `Repository` record is created with `user_id` (stub), source, and status.
- The clone runs inside the sandbox (S1.2) and the working copy is stored on an isolated path.
- No repo-provided hooks or scripts are executed during clone.
- `GET /api/repositories` returns **only** repositories for the current `user_id`.
- *(Scope note: OAuth "connect" for private repos is deferred — public URL + upload only this sprint.)*

### S1.2 — Sandboxed cloning & parsing *(ADR required)*
> **As the** platform, **I want** repository cloning and parsing to run sandboxed — no execution of
> repo-provided code, with clone-size and timeout limits in an isolated filesystem — **so that** a
> malicious repo cannot compromise the platform.

**Acceptance criteria**
- A MADR-format ADR selects the isolation mechanism (docker.sock mount vs nsjail / bubblewrap /
  gVisor / Firecracker) with rationale and trade-offs.
- Cloning/parsing runs with constrained filesystem access and CPU/memory/wall-clock limits.
- A test proves repo-provided code (e.g. a malicious checkout hook or build script) does **not**
  execute on the host.
- Max clone size and timeout are configurable via env vars; oversized/timed-out clones fail
  gracefully with a recorded error status.

### S1.3 — Background job processing
> **As the** platform, **I want** ingestion and scanning to run as background jobs on a Redis-backed
> queue, **so that** long-running work doesn't block HTTP requests.

**Acceptance criteria**
- Redis + an RQ worker service are added to `docker-compose`.
- The ingestion endpoint enqueues work and returns immediately with a scan id.
- A `Scan` record tracks status (`queued` / `running` / `succeeded` / `failed`), scoped by `user_id`.
- `GET /api/scans/{id}` returns status for the owner only.
- A worker failure marks the scan `failed` with an error message — the worker does not crash.
- *(Scope note: prod Redis can use Render's free Key Value instance — ephemeral, data lost on
  restart; acceptable for a portfolio queue.)*

### S1.4 — Owner-scoping from the start
> **As the** platform, **I want** every repository and scan associated with an owner (`user_id`)
> from the start — using a stub user before login exists — **so that** multi-tenancy doesn't
> require a painful retrofit later.

**Acceptance criteria**
- A stub `User` is seeded and a `get_current_user()` dependency returns it.
- `Repository`, `Scan`, and `Finding` tables all carry a non-null `user_id` FK.
- The single initial Alembic migration creates all four tables with their FK constraints.
- Every read endpoint filters by the current `user_id` — no unscoped/global queries.

---

## Dev B — Analysis Engine & Presentation

### S1.5 — Golden dataset of vulnerable repos
> **As a** developer, **I want** a golden dataset of intentionally-vulnerable sample repos with
> labeled findings, **so that** every detector (and the later eval harness) has reference data to
> validate against.

**Acceptance criteria**
- 3–5 intentionally-vulnerable sample repos committed under a fixtures path (or referenced as
  public repos).
- Each repo ships a labeled expected-findings file in the agreed `Finding` format.
- Dockerfile cases cover all 5 checks from S1.7.
- A short README documents the layout and how to add new cases.

### S1.6 — File listing & project-type detection
> **As a** user, **I want** to see the list of files and the detected project type
> (Docker / Kubernetes / Terraform / etc.), **so that** I understand what will be scanned.

**Acceptance criteria**
- A pure function takes a repo path and returns a file manifest + detected project type(s).
- Detection is based on file presence/patterns (e.g. `Dockerfile`, `*.tf`, k8s manifests).
- Runs against golden-dataset fixtures with **no dependency** on the clone pipeline.
- Exposed to the frontend via a scan-result endpoint scoped by `user_id`.

### S1.7 — Dockerfile misconfiguration analysis *(cap: 5 checks)*
> **As a** user, **I want** my Dockerfiles analyzed for common misconfigurations, **so that** I know
> about container risks.

**Acceptance criteria**
- A pure function takes a repo path and returns `Finding` objects for each Dockerfile.
- Exactly 5 checks this sprint:
  1. Container runs as root (no `USER` directive).
  2. Base image pinned to `latest` or untagged.
  3. Hardcoded secret in `ENV` / `ARG`.
  4. `ADD` used to fetch a remote URL (should be a verified `COPY`/download).
  5. Package install without version pinning.
- Each finding carries: rule id, severity, file, line, message.
- Validated against the S1.5 golden-dataset labels.

### S1.8 — Display Dockerfile findings in the frontend
> **As a** user, **I want** the Dockerfile findings displayed in the frontend, **so that** I can
> review them without digging through logs.

**Acceptance criteria**
- `GET /api/scans/{id}/findings` returns findings for the owner (`user_id`-scoped).
- A React + TanStack Query view lists findings grouped by file, with severity.
- Loading, empty, and error states are handled.

---

## Single integration point

End of sprint: Dev A's worker swaps the stub analyzer for Dev B's real `analyze(repo_path)` and
persists the returned `Finding`s. Until then, **Dev A develops against the stub**, **Dev B develops
against golden-dataset fixture paths** — fully parallel.
