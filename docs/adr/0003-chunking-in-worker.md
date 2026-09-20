# ADR-0003 — Chunking runs in the worker, not in the sandbox

**Status:** Accepted  
**Date:** 2026-09-18  
**Authors:** Dev B

---

## Context

Sprint 4 will expose a RAG chatbot that cites specific sections of the
analysed repository. For that to work, repository files must be split into
text chunks and stored in the database before Sprint 4 begins. The question
is *where* in the pipeline this chunking step runs.

Two candidate locations exist:

1. **Inside the sandbox** (`sandbox/entrypoint.py`) — the sandbox already has
   read-only access to the cloned repository and could emit chunks alongside
   findings on stdout.

2. **In the worker** (`jobs.py`) — the worker already reads files from the
   cloned repository (e.g. `clone.py`, `_content_suggests_kubernetes`) and
   has a direct database session.

---

## Decision

Chunking runs **in the worker**, after `generate_report()` completes and
before the scan status is flipped to `succeeded`.

---

## Reasoning

### Security invariant is preserved

`DESIGN.md` states: *"nothing parses or executes untrusted content outside
the sandbox."*

Reading a file as opaque bytes or a raw UTF-8 string is not parsing.
`classify.py`'s `_content_suggests_kubernetes` already does this today, in
the worker, with `errors="replace"` decoding. Chunking follows the same
pattern — it reads text, splits on character boundaries, and stores strings.
No AST, no interpreter, no execution.

### Sandbox stdout contract is stable

The sandbox emits a newline-delimited JSON array of findings. Fabián's
upload feature and the frontend reporting UI both depend on this contract
being simple and predictable. Embedding full file contents in stdout would
inflate each scan run by megabytes and break any tooling that validates or
logs sandbox output.

### Direct database access

The worker already holds an open `SessionLocal` session. The sandbox has no
database connection and would have to pipe data back through stdout anyway,
reintroducing the contract-inflation problem.

### Simplicity

Keeping chunking in the worker means a single, linear call sequence:
~~~
clone_repo → _run_sandbox → create_findings → generate_report → chunk_scan_files → update_scan(succeeded)
~~~


No new IPC, no stdout schema changes, no sandbox rebuild.

---

## Hard limits enforced in the worker

To prevent a malicious or unusually large repository from exhausting storage:

| Limit | Value | Location |
|---|---|---|
| Files chunked | text categories only (`classify_file` result != `"unknown"`) | `chunk_scan_files` caller |
| Max chunks per file | 50 | `chunk_services.MAX_CHUNKS_PER_FILE` |
| Max chunks per scan | 2 000 | `chunk_services.MAX_CHUNKS_PER_SCAN` |
| Decoding errors | `errors="replace"` | caller before `chunk_scan_files` |
| Parsing | none — character-boundary splits only | by design |

---

## Sprint 4 requirement

Chunks are stored as raw text segments from an untrusted repository.
**Sprint 4 must sanitise chunk content before inserting it into LLM prompts**
to prevent prompt-injection attacks.

---

## Alternatives considered

### Option A — Chunking inside the sandbox

- Pros: physically isolated from the host.
- Cons: inflates stdout with full file contents; breaks the stable findings
  contract; requires the sandbox to have a DB connection or a new IPC channel;
  sandbox container must be rebuilt when chunking logic changes.

### Option B — Separate chunking worker / queue job

- Pros: decoupled lifecycle.
- Cons: adds a second job type, a new queue, and race conditions between the
  scan job and the chunk job. Premature for Sprint 3 scope.

---

## Consequences

- `chunk_scan_files` is called from `run_scan` in `jobs.py` (implemented in
  branch `feature/scan-chunking-pipeline`).
- `inspect_repo` in `classify.py` (currently dead code) is the canonical file
  selector that feeds `chunk_scan_files`.
- The `Chunk` model has no `embedding` column. Sprint 4 will add it once the
  LLM provider and vector dimension are decided.