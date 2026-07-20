# Golden Dataset — Fixture README

## Directory layout

```
fixtures/
├── finding-schema.yaml          # Canonical Finding field definitions & severity guide
├── README.md                    # This file
│
├── repo-root-user/              # DF001 — container runs as root
│   ├── Dockerfile
│   ├── expected-findings.yaml
│   └── url.md                   # (optional) Real-world repo reference
│
├── repo-latest-tag/             # DF002 — base image pinned to :latest
│   ├── Dockerfile
│   ├── expected-findings.yaml
│   └── url.md                   # (optional) Real-world repo reference
│
├── repo-hardcoded-secrets/      # DF003 — secrets in ENV / ARG
│   ├── Dockerfile
│   ├── expected-findings.yaml
│   └── url.md                   # (optional) Real-world repo reference
│
├── repo-add-remote-url/         # DF004 — ADD fetches a remote URL
│   ├── Dockerfile
│   ├── expected-findings.yaml
│   └── url.md                   # (optional) Real-world repo reference
│
└── repo-unpinned-packages/      # DF005 — packages installed without version pins
    ├── Dockerfile
    ├── expected-findings.yaml
    └── url.md                   # (optional) Real-world repo reference
```

Each fixture repo maps to exactly one primary rule so that detector unit tests
can assert a single, unambiguous expected output.  A fixture may carry
*multiple findings* when the same rule fires on several lines (e.g.
`repo-hardcoded-secrets` has two DF003 hits, `repo-add-remote-url` has two
DF004 hits).

---

## Finding format

All `expected-findings.yaml` files use the schema defined in
[`finding-schema.yaml`](./finding-schema.yaml).

```yaml
findings:
  - rule_id:  DF001          # string  — rule identifier
    severity: HIGH           # enum    — CRITICAL|HIGH|MEDIUM|LOW|INFO
    file:     Dockerfile     # string  — repo-relative path
    line:     null           # int|null — 1-based line; null = whole-file finding
    message:  >              # string  — explanation + remediation hint
      No USER directive found …
```

The detector is expected to return objects with these exact five fields.
The eval harness compares detector output against `expected-findings.yaml`
matching on `(rule_id, file, line)` — the `message` field is not compared
for equality but must be non-empty.

---

## Real-world repo references (url.md)

Each fixture may include a `url.md` file referencing real open-source
repositories whose code exhibits the same vulnerability class. These are
intended for integration / end-to-end tests that validate the detector
against real-world code (not just minimal fixtures).

The file uses a Markdown table with the following columns:

| Column | Description |
|--------|-------------|
| Repo | Link to the GitHub repository |
| Reason | What vulnerability it demonstrates and why it matches the fixture |

Clone URLs (HTTPS and SSH) are listed below the table when available.

A fixture may omit `url.md` entirely if no suitable real-world repository
has been identified yet.

---

## Rule catalogue (S1.7 — 5 checks)

| Rule ID | Severity | Description |
|---------|----------|-------------|
| DF001 | HIGH | No `USER` directive — container runs as root |
| DF002 | MEDIUM | Base image uses `:latest` tag or is untagged |
| DF003 | CRITICAL | Hardcoded secret in `ENV` or `ARG` default value |
| DF004 | HIGH | `ADD` used to fetch a remote URL |
| DF005 | MEDIUM | Package install (`apt-get`, `pip`, `npm`, etc.) without version pinning |

---

## How to add a new fixture case

1. **Create a new subdirectory** under `fixtures/` with a descriptive name
   (e.g. `repo-privileged-mode` for a future DF006 check).

2. **Add the vulnerable file(s)** — typically a `Dockerfile`, but can also be
   a Kubernetes manifest, Terraform file, etc. as the detector surface grows.

3. **Write `expected-findings.yaml`** following the schema in
   `finding-schema.yaml`.  Every finding that the detector *should* emit must
   be listed.  Do **not** list findings the detector should *ignore* — the
   harness treats any unlisted finding emitted by the detector as a false
   positive.

4. **Keep each fixture focused** — one primary rule per fixture directory.
   If you need to test rule interaction, create a dedicated
   `repo-combined-<ruleA>-<ruleB>/` fixture and document the intent in a
   comment at the top of the `Dockerfile`.

5. **Run the eval harness** to confirm all labels pass before opening a PR:
```bash
   cd backend
   uv run pytest tests/eval -v
```

---

## Conventions

- Dockerfiles are minimal — only the lines needed to trigger (or not trigger)
  the rule under test.  Avoid adding realistic application code that might
  accidentally trigger *other* rules and pollute the expected-findings list.
- Line numbers in `expected-findings.yaml` must stay in sync with the
  `Dockerfile`.  If you edit a Dockerfile, re-check every `line:` value.
- Use `line: null` only for **whole-file** findings where no single line can
  be cited (currently only DF001 — missing USER).
