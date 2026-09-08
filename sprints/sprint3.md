# Sprint 3 — Reporting UI & Export (expanded) _(MVP 1 complete)_

**Split rationale:** Developer A owns the repository-connect and findings/report-viewing surface — mostly reads
against existing endpoints (`GET /api/scans/{id}`, `/findings`, `/report`), two new read-only endpoints they own
themselves, and one write path (repository upload) that extends `POST /api/repositories`. Developer B owns the
export and RAG-prep pipeline work (`jobs.py`, new export routes, new `Chunk` model) that never touches the
frontend. Neither track calls into anything the other track is building, so both can run in parallel all sprint.

---

## Developer A — Findings & Report Experience

Frontend-heavy: how findings and reports render and are navigated, plus two small new read endpoints.

### Reporting UI

- _(Revised)_ As a user, I want findings grouped by severity (critical/high/medium/low/info) in the report view,
  in addition to the existing category/file grouping, so I can prioritize fixes. _(Report generation and
  severity counts already exist — `reporting/generate.py`, `ReportSummary.tsx` — this story is scoped to adding
  the missing grouped-by-severity findings list.)_

  **Acceptance criteria:**
  - Report page offers a toggle/tab between "By file" (existing) and "By severity" views.
  - "By severity" view buckets findings under Critical/High/Medium/Low/Info headers, matching the key set of
    `ReportResponse.severity_counts`.
  - Each bucket's displayed count matches `severity_counts[<severity>]` exactly.
  - Empty severity buckets (count 0) are omitted, not rendered as empty sections.
  - Within a bucket, findings are sorted by file path, then line number.

- As a user, I want to filter/search findings by severity, category, or rule ID so I can focus on what matters in
  a large findings list.

  **Acceptance criteria:**
  - Filter controls exist for severity, category (`docker`/`kubernetes`), and rule ID.
  - Filters are combinable with AND logic and update the list without a full page reload.
  - A "clear filters" control resets to the unfiltered list.
  - The visible/total count is shown (e.g. "12 of 47 findings").
  - Filters apply in both the by-file and by-severity (above) views.

- As a user, I want to see a clear error state when a scan fails (with the recorded error message) so I'm not
  left looking at a blank or stuck screen.

  **Acceptance criteria:**
  - When `GET /api/scans/{id}` returns `status: "failed"`, an error panel replaces the findings/report view.
  - The panel displays the `error` field already present on `ScanResponse` (no backend change needed).
  - The error state offers a way to retry (links to the re-scan action below) or return to the connect form.
  - `queued`/`running` status continues to show the existing polling/progress UI, unaffected.

- As a user, I want to see a list of my connected repositories and their scan history so I can navigate back to
  previous results without re-entering a scan ID. _(Requires new `GET /api/repositories` and
  `GET /api/repositories/{id}/scans` endpoints — neither exists today.)_

  **Acceptance criteria:**
  - `GET /api/repositories` returns the current user's repositories, owner-scoped via `current_user.id`
    (mirrors the existing pattern in `repository_services.py`).
  - `GET /api/repositories/{id}/scans` returns that repo's scans ordered most-recent-first; 404s if the repo
    isn't owned by the current user.
  - Frontend landing view lists connected repositories with each one's latest scan status.
  - Selecting a repository shows its scan history (status, started/finished timestamps) linking into each scan's
    report.
  - An empty state ("no repositories yet") is shown when the list is empty.

- As a user, I want to trigger a re-scan of an already-connected repository from the UI so I don't have to
  re-paste its git URL every time.

  **Acceptance criteria:**
  - A "Re-scan" button on a repository's detail/history view calls the existing `POST /api/scans` with that
    repo's `repository_id`.
  - The button is disabled while a scan for that repo is already `queued`/`running`.
  - After triggering, the UI navigates to/polls the new scan the same way the initial connect flow does.
  - The new scan appears at the top of the repo's scan history once created.

### Bug fix

- As a developer, I want the frontend's severity badge/rank set (`FindingsByFile.tsx`) reconciled with the
  backend's 5-level severity scale (`critical/high/medium/low/info`) so `critical` and `info` findings render
  correctly instead of falling through the current `high/medium/low`-only mapping. _(Real bug found during this
  audit, not a hypothetical — bundled here since it touches the same file as the severity-grouped view story
  above.)_

  **Acceptance criteria:**
  - `SEVERITY_RANK` and `SEVERITY_BADGE_VARIANT` cover all 5 backend severities.
  - A finding with severity `critical` or `info` renders with its own distinct badge style, not a fallback.
  - Sort order places `critical` above `high`, and `info` below `low`.
  - Existing `high`/`medium`/`low` rendering is unchanged (regression check).

### Repository connect

- As a user, I want to upload a repository as a `.zip`/`.tar` archive (not just connect via git URL) so MVP1's
  own pitch ("a user can upload a repo") is actually true by the end of this sprint. _(`Repository.source_type`
  already has an `upload` value in the schema per DESIGN.md's ERD — this wires up the missing ingestion path.
  Grouped here since it's a third way of getting a repo connected, alongside the repo-list and re-scan stories
  above, rather than part of the export/chunking pipeline.)_

  **Acceptance criteria:**
  - `POST /api/repositories` (or a new endpoint) accepts a `.zip`/`.tar` upload and creates a `Repository` with
    `source_type: "upload"`.
  - Uploaded archives respect size/time limits analogous to `ingestion/clone.py`'s existing clone limits.
  - `jobs.py`'s `Unsupported source type` branch in `run_scan` gains an `upload` case that extracts the archive
    instead of git-cloning.
  - Malformed/oversized archives are rejected with a clear 4xx error before reaching the sandbox.
  - An uploaded repo scans successfully end-to-end (findings + report generated), verified against a fixture
    archive.

---

## Developer B — Export & RAG Prep

Backend/pipeline-heavy: new export routes and chunking groundwork for Sprint 4.

### Export

- As a user, I want to export my security report as Markdown so I can paste it into an issue, PR description, or
  documentation.

  **Acceptance criteria:**
  - New endpoint (e.g. `GET /api/scans/{id}/report/export?format=markdown`) returns a Markdown document with
    `Content-Type: text/markdown`.
  - Document includes repo name, scan timestamp, `total_findings`, severity/category/rule counts, and the full
    findings list grouped by severity.
  - Returns 409 if the scan hasn't `succeeded` (same guard as the existing `get_scan_report`).
  - Returns 404 for a scan not owned by the current user.
  - Response has a sensible filename, e.g. `<repo-name>-<scan-id>.md`.

- As a user, I want to export my security report as PDF so I can share a polished report outside the platform.

  **Acceptance criteria:**
  - Same endpoint with `format=pdf` returns a PDF with `Content-Type: application/pdf`.
  - Same content coverage as the Markdown export (counts + full findings list grouped by severity).
  - Same 409/404 ownership guards as the Markdown export.
  - Renders correctly in a standard PDF viewer on both a 0-finding report and a 50+-finding report (manually
    verified).

- **As a developer, I want export generation covered by tests (using existing fixture repos) so exported report
  content is verified to match the persisted findings/report, not just "renders without crashing."**

  **Acceptance criteria:**
  - A test generates a Markdown export from a known `Report`/`Finding` fixture set and asserts all counts and
    finding titles appear in the output.
  - An equivalent test for PDF (e.g. extract text from the generated PDF and assert key content is present).
  - Tests cover the 409 case (scan not succeeded) and the 404 case (wrong owner).
  - Tests follow the existing pattern in `backend/tests/test_reporting.py` / `test_report_persistence.py`.

### Chunking (RAG prep)

- **As a system, I want a `Chunk` model and persistence layer (source path, content, chunk index, token count) so
  scanned file content can be stored in fixed-size retrievable segments per scan run, ready for Sprint 4's
  embedding step.**

  **Acceptance criteria:**
  - New `Chunk` model matches DESIGN.md's ERD (`scan_run_id` FK, `source_path`, `content`, `chunk_index`,
    `token_count`), plus an Alembic migration.
  - New `chunk_services.py` follows the existing service pattern (owner-scoped where applicable, mirroring
    `report_services.py`).
  - Chunk-to-scan FK uses `ondelete="CASCADE"`, matching `Report`'s existing pattern
    (`backend/app/models/report.py:22-23`).
  - Chunking strategy (size/overlap) is documented in code or a short ADR note, since it constrains Sprint 4.

- As a system, I want chunking to run automatically at the end of a successful scan job (alongside report
  generation) so content is ready without a separate manual step.

  **Acceptance criteria:**
  - `jobs.run_scan` calls chunking alongside the existing `generate_report` call, only when the scan succeeds.
  - Chunking failure doesn't fail the whole scan — findings/report stay available even if chunking errors,
    logged rather than raised (matches `run_scan`'s existing try/except pattern).
  - No `Chunk` rows are created for a `failed` scan.

- **As a developer, I want chunking behavior unit-tested (boundary conditions, token counts, non-empty content,
  no chunks on a failed scan) so Sprint 4 can trust this input without re-verifying it.**

  **Acceptance criteria:**
  - Test asserts correct chunk boundaries for a multi-file fixture repo (expected chunk count, sequential
    `chunk_index` per file).
  - Test asserts `token_count` is non-zero and roughly proportional to content length.
  - Test asserts no chunks exist for a failed scan.
  - Tests follow existing patterns in `backend/tests/`.

### Quality / hardening

- **As a developer, I want a small end-to-end test that exercises the full pipeline (connect repo → scan →
  findings → report → export) against a fixture repo so the MVP1 walking skeleton is proven as a whole, not just
  as isolated units.**

  **Acceptance criteria:**
  - One test drives: create repository → create scan → run job (synchronously or against a test queue) → assert
    findings persisted → assert report generated → assert export produces non-empty output.
  - Runs against an existing golden-dataset fixture repo (`fixtures/Docker/...` or `fixtures/K8s/...`).
  - Runs in CI alongside the existing backend test suite (`uv run pytest`).
