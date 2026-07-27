# Golden Dataset — Fixture README

## Directory layout

Fixtures are grouped by analyzer category, each with its own
`finding-schema.yaml`:

```
fixtures/
├── README.md                    # This file
│
├── Docker/
│   ├── finding-schema.yaml      # Canonical Finding field definitions & severity guide (Docker)
│   ├── repo-root-user/          # DF001 — container runs as root
│   │   ├── Dockerfile
│   │   ├── expected-findings.yaml
│   │   └── url.md               # (optional) Real-world repo reference
│   ├── repo-latest-tag/         # DF002 — base image pinned to :latest
│   ├── repo-hardcoded-secrets/  # DF003 — secrets in ENV / ARG
│   ├── repo-add-remote-url/     # DF004 — ADD fetches a remote URL
│   └── repo-unpinned-packages/  # DF005 — packages installed without version pins
│
└── K8s/
    ├── finding-schema.yaml      # Canonical Finding field definitions & severity guide (Kubernetes)
    ├── repo-privileged/         # K8S001 — privileged container
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   ├── expected-findings.yaml
    │   └── url.md               # (optional) Real-world repo reference
    ├── repo-hostnetwork/        # K8S002 — hostNetwork/hostPID/hostIPC
    ├── repo-missing-limits/     # K8S003 — missing resource requests/limits
    ├── repo-privilege-escalation/ # K8S004 — allowPrivilegeEscalation not false
    └── repo-root-user/          # K8S005 — missing runAsNonRoot
```

Each fixture repo maps to exactly one primary rule so that detector unit tests
can assert a single, unambiguous expected output.  A fixture may carry
*multiple findings* when the same rule fires on several lines (e.g.
`Docker/repo-hardcoded-secrets` has two DF003 hits, `Docker/repo-add-remote-url`
has two DF004 hits). K8s fixtures additionally carry a `service.yaml` — a
plain `Service` manifest with no pod spec — to prove the detector doesn't
false-positive on non-workload manifests sitting in the same repo.

---

## Finding format

All `expected-findings.yaml` files use the schema defined in that category's
`finding-schema.yaml` (e.g. [`Docker/finding-schema.yaml`](./Docker/finding-schema.yaml),
[`K8s/finding-schema.yaml`](./K8s/finding-schema.yaml)) — identical five-field
shape across categories, only the `rules:` catalogue differs.

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

## Rule catalogue

### Docker (S1.7 — 5 checks)

| Rule ID | Severity | Description |
|---------|----------|-------------|
| DF001 | HIGH | No `USER` directive — container runs as root |
| DF002 | MEDIUM | Base image uses `:latest` tag or is untagged |
| DF003 | CRITICAL | Hardcoded secret in `ENV` or `ARG` default value |
| DF004 | HIGH | `ADD` used to fetch a remote URL |
| DF005 | MEDIUM | Package install (`apt-get`, `pip`, `npm`, etc.) without version pinning |

### Kubernetes (S2.1 — 5 checks)

| Rule ID | Severity | Description |
|---------|----------|-------------|
| K8S001 | HIGH | Privileged container (`securityContext.privileged: true`) |
| K8S002 | HIGH | `hostNetwork`, `hostPID`, or `hostIPC` set to `true` |
| K8S003 | MEDIUM | Container missing resource `requests`/`limits` (cpu and/or memory) |
| K8S004 | HIGH | `allowPrivilegeEscalation` not explicitly set to `false` |
| K8S005 | MEDIUM | Container missing `runAsNonRoot: true` |

---

## How to add a new fixture case

1. **Create a new subdirectory** under the relevant category
   (`fixtures/Docker/` or `fixtures/K8s/`) with a descriptive name
   (e.g. `repo-privileged-mode` for a future DF006 check).

2. **Add the vulnerable file(s)** — a `Dockerfile` under `Docker/`, a
   Kubernetes manifest under `K8s/`, or a Terraform file if/when that
   category is added.

3. **Write `expected-findings.yaml`** following the schema in that
   category's `finding-schema.yaml`.  Every finding that the detector
   *should* emit must be listed.  Do **not** list findings the detector
   should *ignore* — the harness treats any unlisted finding emitted by the
   detector as a false positive.

4. **Keep each fixture focused** — one primary rule per fixture directory.
   If you need to test rule interaction, create a dedicated
   `repo-combined-<ruleA>-<ruleB>/` fixture and document the intent in a
   comment at the top of the vulnerable file.

5. **Run the eval harness** to confirm all labels pass before opening a PR:
```bash
   cd backend
   uv run pytest tests/eval -v
```

---

## Conventions

- Fixture files are minimal — only the lines needed to trigger (or not
  trigger) the rule under test.  Avoid adding realistic application code
  that might accidentally trigger *other* rules and pollute the
  expected-findings list.
- Line numbers in `expected-findings.yaml` must stay in sync with the
  fixture file.  If you edit it, re-check every `line:` value.
- Use `line: null` only for **whole-file** findings where no single line can
  be cited (currently only DF001 — missing USER). For findings caused by a
  *missing* key where a containing block still exists (e.g. K8S003/004/005 —
  a container missing `resources`, `allowPrivilegeEscalation`, or
  `runAsNonRoot`), anchor on the container's `- name: <container>` line
  instead of `null`, so the finding still points somewhere actionable.
- K8s fixtures pair each vulnerable manifest with a deliberately compliant
  `service.yaml` to confirm the detector doesn't false-positive on
  non-workload manifests in the same repo.
