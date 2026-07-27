# Sprint 2 — Kubernetes Analysis, Persistence & Reporting

Continues from Sprint 1 (repository ingestion, sandboxing, Dockerfile analysis — see
sprints/sprint1.md). 

Target: MVP 1 close-out groundwork (MVP 1 completes end of Sprint 3 per PLAN.md).

## Shared kickoff (freeze before branching)

1. **`findings.category` extended to `"kubernetes"`** (already anticipated in DESIGN.md's ERD) —
   one Alembic migration, agreed upfront so both devs branch from the same schema.
2. **Kubernetes analyzer output uses the identical Finding schema** as
   `backend/analysis/docker.py` (`rule_id`, `severity`, `file`, `line`, `message`, `remediation`,
   `category`) — so the report generator and eval harness can treat all analyzers generically,
   with no docker/kubernetes special-casing.
3. **New `reports` table schema frozen up front**: `id`, `scan_id` (FK), `user_id` (FK),
   `severity_counts` (JSONB), `rule_counts` (JSONB), `category_counts` (JSONB),
   `total_findings`, `created_at`. One migration, reviewed by both devs since the frontend
   report view consumes this shape directly.
4. **Golden-dataset convention extends unchanged**: new `fixtures/repo-k8s-*/` directories,
   each with a manifest file + `expected-findings.yaml`, following `fixtures/README.md`'s
   existing rules.
5. **Sequencing note**: the CI eval-harness story (S2.4) depends on the Kubernetes analyzer
   (S2.1) landing, or ships Docker-only first and is extended once S2.1 merges. Sync mid-sprint
   on this handoff.

---

## Dev A — Analysis Engine & Presentation (rotated from Sprint 1's Platform role)

### S2.1 — Kubernetes manifest misconfiguration analysis (cap: 5 checks)

*As a user, I want my Kubernetes manifests analyzed for common misconfigurations so I know
about cluster-level risks.*

**Acceptance criteria:**
- New `backend/analysis/kubernetes.py`, mirroring `analysis/docker.py`'s pure-function
  structure (`analyze(repo_path) -> list[Finding]`), parsing manifests
  (Pod/Deployment/StatefulSet/DaemonSet pod-template specs). Exactly 5 checks:
  - **K8S001** (HIGH) — privileged container (`securityContext.privileged: true`)
  - **K8S002** (HIGH) — `hostNetwork`, `hostPID`, or `hostIPC` set to `true`
  - **K8S003** (MEDIUM) — container missing resource `requests`/`limits` (cpu and/or memory)
  - **K8S004** (HIGH) — `allowPrivilegeEscalation` not explicitly set to `false`
  - **K8S005** (MEDIUM) — container missing `runAsNonRoot: true`
- Findings emitted with `category="kubernetes"`, same 5-field schema as Docker findings.
- **`ingestion/classify.py`'s existing project-type detection is finally wired into the live
  pipeline** (sandbox entrypoint or a small dispatcher) to decide whether to run the Docker
  analyzer, Kubernetes analyzer, or both per repo — this closes a Sprint 1 gap where
  `classify.py` was implemented and tested but never called outside tests.
- 5 new golden-dataset fixtures: `repo-k8s-privileged`, `repo-k8s-hostnetwork`,
  `repo-k8s-missing-limits`, `repo-k8s-privilege-escalation`, `repo-k8s-root-user`, each with a
  minimal manifest + `expected-findings.yaml`.
- Unit tests in `backend/tests/test_kubernetes_analysis.py`, mirroring
  `test_docker_analysis.py`'s positive/negative coverage per rule.
- `fixtures/README.md`'s rule catalogue table extended with the K8S00x rows.

### S2.2 — Display Kubernetes findings & report summary in the frontend

*As a user, I want to see Kubernetes findings and an at-a-glance report summary, so I can act
on cluster-level risk alongside Docker risk.*

**Acceptance criteria:**
- Findings grouped/labeled by `category` (docker vs kubernetes) so mixed-category scan results
  are legible (e.g. a badge or section header per category) in the existing findings view.
- New section consuming `GET /api/scans/{id}/report` (Dev B's S2.3) to show the
  severity/rule-count summary above the per-file findings list.
- Loading/empty/error states handled for the new report view, consistent with the existing
  `ScanStatus`/`FindingsByFile` patterns.
- Reuses existing shadcn primitives already in `components/ui/` — no new UI dependencies.

---

## Dev B — Platform & Persistence (rotated from Sprint 1's Analysis role)

### S2.3 — Report generation & persistence

*As a system, I want a report generation process that summarizes all findings from a scan run,
so reports can be produced consistently.*

**Acceptance criteria:**
- New `reports` table via Alembic migration (schema frozen in shared kickoff above).
- New `backend/reporting/` module: `generate_report(scan_id) -> Report`, a pure aggregation
  function (counts by severity, by rule_id, by category, total findings).
- `jobs.run_scan` calls report generation automatically as the final step once findings are
  persisted and before the scan is marked `succeeded` — every succeeded scan has a report with
  no separate manual trigger.
- New endpoint `GET /api/scans/{id}/report` — owner-scoped (404 if not found/not owned), returns
  a clear 409/422 if the scan hasn't succeeded yet.
- Unit tests: aggregation math against seeded findings; API tests for owner-scoping and
  not-ready state.
- Note: "scan results stored in PostgreSQL" (PLAN.md's original story wording) is already
  satisfied by Sprint 1's `Scan`/`Finding` tables — this story's actual gap is the *aggregate
  report*, not raw persistence.

### S2.4 — Golden-dataset regression gate in CI

*As a developer, I want the detectors validated against the golden dataset in CI, so detection
accuracy is measured continuously as rules are added.*

**Acceptance criteria:**
- `backend/tests/eval/test_golden_dataset.py`: for every fixture directory under `fixtures/`,
  runs the appropriate analyzer against the fixture file, parses `expected-findings.yaml`, and
  asserts an exact match on `(rule_id, file, line)` — catching both missing findings and
  unexpected extras (false positives).
- Ships with Docker-fixture coverage first if S2.1 hasn't landed yet; extended to Kubernetes
  fixtures once it does (see shared-kickoff sequencing note).
- `fixtures/README.md`'s placeholder eval command (currently "TBD") replaced with the real
  `pytest` invocation.
- Wired as a required step in `.github/workflows/ci.yml`'s backend job — a detector regression
  now fails CI.

---

## Technical Debt

Carried over from Sprint 1, found by reading the actual implementation (not comment-flagged —
none of this is marked TODO/FIXME in the code, so it's easy to miss without a direct look).
Not scored as sprint stories; listed here so it's visible and can be triaged deliberately.

1. **Archive-upload scans are silently broken.** `POST /api/repositories/upload` accepts a
   file, creates `Repository`/`Scan` rows, and enqueues a scan — but `jobs.run_scan` immediately
   raises (`Unsupported source type for scanning: upload`) because the uploaded bytes are never
   stored or unpacked anywhere (`upload_key` is written but never read back). Every upload-based
   scan the API currently accepts is guaranteed to fail after the fact.
   _Owner: Dev B — commit this sprint (user-facing flow is currently broken)._
   **Look at:** either reject upload requests explicitly at the API layer (4xx with a clear
   message, and hide/disable the option in the frontend) until real support is built, or
   schedule full implementation (archive storage + extraction into the sandbox flow, size
   limits, tests) for a future sprint. Leaving it silently broken is the one option to avoid.

2. **Sandbox / Docker-in-Docker path has no CI coverage.** `jobs._run_sandbox` and the sandbox
   image itself are never built or exercised in CI — the core security boundary of the product
   is implemented but automated-unverified.
   _Owner: Dev B — backlog-only this sprint (not committed alongside S2.3/S2.4)._
   **Look at:** add a CI job that builds the sandbox image and runs a real scan against a golden
   fixture end-to-end.

3. **No test proves malicious repo hooks don't execute on the host.** This was an explicit
   Sprint 1 / ADR-0002 acceptance criterion (S1.2) that was never actually written.
   _Owner: Dev B — commit this sprint (explicit security-boundary gap)._
   **Look at:** add a fixture repo with a malicious `post-checkout`/`pre-commit` hook and a test
   asserting it never runs. Security-relevant, not just polish — worth prioritizing over other
   debt items here.

4. **`render.yaml` defines no worker service.** There's a web service for the backend and a
   static service for the frontend, but no deployed RQ worker and no Docker-socket access
   configured — unclear whether scans can actually run at all in the deployed environment.
   ADR-0002 accepted the docker.sock exposure as a known risk but nothing confirms it's been
   proven working on Render specifically.
   _Owner: Dev B — backlog-only this sprint (not committed alongside S2.3/S2.4)._
   **Look at:** verify (or build) a real deployed path for the worker before relying on the
   hosted demo for anything user-facing.

5. **`CLAUDE.md` is stale.** It still describes the pre-Sprint-1 walking-skeleton state: says
   ingestion/sandbox/analysis "don't exist yet," calls out `backend/sandbox/Dockerfile` as an
   "unwired stub" (false — it's wired), says there's "no separate worker entrypoint yet" (false —
   `backend/worker.py` exists), and references `frontend/src/api.ts` (replaced by
   `frontend/src/features/api/*.ts` + `lib/api-client.ts`).
   _Owner: unassigned — quick win for whoever finishes their committed stories first._
   **Look at:** cheap, high-value fix — update it to reflect Sprint 1's actual delivered state.

6. **`jobs.run_scan` and `ingestion/clone.py`'s `clone_repo` have no direct unit tests.** They're
   only exercised implicitly through Redis-dependent API tests — the core worker state machine
   (`queued`→`running`→`succeeded`/`failed`, error persistence, findings mapping) has no fast,
   mocked unit test.
   _Owner: Dev B — backlog-only this sprint (not committed alongside S2.3/S2.4)._
   **Look at:** add tests that mock Docker/clone to verify status transitions and error handling
   without needing a live Redis/Docker environment.

7. **Frontend has zero test coverage** (no vitest config, no `*.test.tsx`). Not urgent given the
   TanStack Query hooks are thin wrappers, but worth revisiting once S2.2's report UI lands and
   the component surface grows.
   _Owner: Dev A._

8. **`react-router-dom` is an unused dependency.** `App.tsx` hand-rolls URL state via
   `URLSearchParams`/`history.replaceState` instead of using the router that's already installed.
   _Owner: Dev A._
   **Look at:** either wire it in when real routing is needed, or drop the dependency so it
   doesn't imply routing exists when it doesn't.

9. **Latent falsy-zero bug in `FindingsByFile.tsx`.** `{finding.line_number && ...}` will
   silently hide a legitimate `line_number === 0`. Low risk today (Dockerfile/K8s findings are
   1-based), but worth fixing opportunistically while S2.2 touches this file — use
   `!= null` instead of truthiness.
   _Owner: Dev A — fold into S2.2 while that file is already being touched._
