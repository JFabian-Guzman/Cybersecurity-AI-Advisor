# Architecture Decision Records

This directory records the significant architectural and process decisions for the
project. Each record is immutable once accepted: to change a decision, add a new ADR
that supersedes the old one rather than editing history.

## Conventions

- Files are named `NNNN-short-title.md`, numbered sequentially from `0001`.
- Copy `0000-adr-template.md` to start a new record.
- Status moves through: `proposed` → `accepted` → `deprecated` / `superseded by ADR-XXXX`.
- ADRs are reviewed in the same pull request as the work they describe.

## Index

- [0001 - Technology stack and branching strategy](0001-technology-stack-and-branching-strategy.md)
- [0002 - Sandbox isolation mechanism](0002-sandbox-isolation-mechanism.md)
