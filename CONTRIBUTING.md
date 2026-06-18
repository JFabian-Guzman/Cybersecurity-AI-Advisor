## Code standards

- Python: `ruff` + `black` for linting/formatting, type hints required, `mypy` in CI
- TypeScript/React: `eslint` + `prettier`, strict mode enabled
- No secrets committed (enforced via pre-commit hook **and** CI secret scan — fitting for this project)
- Use descriptive, self-explanatory names for variables, functions, and classes — the name should make the purpose obvious without needing a comment.
- Follow **snake_case** for variables and functions, **camelCase** for files.
- Lines must not exceed **120 characters**.
- Keep functions and methods **short and focused** — each one should do exactly one thing.
- Apply the **KISS principle** (Keep It Simple): prefer the simplest solution that works. Avoid over-engineering.
- Apply the **DRY principle** (Don't Repeat Yourself): if logic appears more than once, extract it. Changes should only ever need to be made in one place.
- Comment **why** something is done, not what — the code itself should explain the what.
- Avoid redundant comments that simply restate the code in plain English.
- Provide meaningful, actionable error messages that help identify what went wrong and where.

### Git

#### Branches

- `main` — always deployable, tagged at the end of each sprint (e.g. `v0.1.0`, `v0.2.0`...)
- `develop` — integration branch
- `feature/<short-description>` — one branch per user story
- `fix/<short-description>` — bug fixes off `develop` (or `main` for urgent issues)

#### Workflow

1. Branch `feature/...` off `develop`
2. Commit using Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`)
3. Open PR into `develop`; CI must pass (lint + tests + secret scan)
4. PR reviewed by the other developer before merge
    - If no review within 48h, self-merge is allowed (avoid blocking part-time schedules)
5. At sprint end: merge `develop` → `main`, tag release, and the tagged commit auto-deploys to the live environment

## Testing