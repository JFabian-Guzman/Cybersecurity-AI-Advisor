# 0004. Branching strategy

- Status: accepted
- Date: 2026-06-22
- Deciders: Fabián Guzmán, Andrés Víquez

## Context

The team is two part-time developers. We want sprint-based releases, a reviewed path
from feature to deploy, and a `main` branch that is always safe to deploy. The day-to-day
rules live in [CONTRIBUTING](../../CONTRIBUTING.md); this record captures why we chose
the model. Split out of [0001](0001-technology-stack.md), where it was originally
recorded together with the stack.

## Decision

We will use a GitFlow branching model:

- `main` is always deployable and tagged at each sprint end (e.g. `v.1`, `v.2`).
- `develop` is the integration branch.
- `feature/<short-description>` and `fix/<short-description>` branch off `develop`.
- Commits follow Conventional Commits; every PR must pass CI (lint, tests, secret
  scan) and be reviewed by the other developer before merge. If no review arrives
  within 48 hours, the author may self-merge so part-time schedules do not block work.
- At sprint end, `develop` merges to `main` and the release is tagged.
- Pushing a `v*` tag triggers the deploy workflow, which deploys backend and frontend
  to Render via deploy hooks (`.github/workflows/deploy.yml`).

## Consequences

### Positive

- A predictable, reviewable path from feature to deploy.
- Deploys happen only on tagged releases, so `develop` can be unstable without
  affecting the live environment.

### Negative

- GitFlow adds branch overhead that a two-person team must keep disciplined about,
  mitigated by the 48-hour self-merge rule in CONTRIBUTING.
- Self-merging after 48 hours means some changes ship without a second pair of eyes.
- Every deploy is a full sprint release; there is no continuous delivery of small
  changes.

