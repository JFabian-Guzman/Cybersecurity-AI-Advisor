## MVPs

### MVP 1 — Static Security Scanner (end of Sprint 3)

A working app where a user can upload a repo, get it scanned for Docker/Kubernetes misconfigurations, and view/export a severity-ranked report. No AI yet — this is the "boring but functional" foundation. Ingestion is sandboxed and runs as a background job, repos/scans are already scoped to an owner, and the walking-skeleton deploy is live.

### MVP 2 — AI Security Assistant (end of Sprint 5)

Adds the RAG pipeline and chatbot: users can ask natural-language questions about their repo and get cited, context-grounded answers, with basic prompt-injection defenses since the indexed content is untrusted.

### MVP 3 — Full Product (end of Sprint 7)

Adds secret detection, scan-diffing, the login UI, observability, deployment polish, and final UI cleanup. This is the version demoed to recruiters/portfolio.

## Sprints
### Sprint 0 — Project Setup (2 weeks)

- As a developer, I want the repository initialized with GitFlow branches and branch protection rules so the team has a consistent workflow.
- As a developer, I want to define and document our code standards so that both developers write consistent, maintainable code from the start.
- As a developer, I want to define the technologies we will use so the team agrees on a consistent stack before development starts and can document the decision in an ADR.
- As a developer, I want a docker-compose setup with the defined technologies (e.g. Postgres, Redis, FastAPI, React + Vite) skeletons so both services run locally with one command.
- As a developer, I want CI configured to run lint, tests, and a secret scan on every PR so code quality and hygiene are enforced automatically.
- As a developer, I want an ADR template and a first ADR documenting our stack and branching choices so decisions are traceable.
- As a developer, I want a working "hello world" round trip (frontend → backend → database) so the environment is verified end-to-end.
- **As a developer, I want the hello-world round trip deployed to a live environment (walking skeleton) so deployment risk is found in week 2, not week 15.**

---

### Sprint 1 — Repository Ingestion, Sandboxing & Dockerfile Analysis

- As a user, I want to upload or connect a Git repository so the system can clone and store it for analysis.
- **As a system, I want repository cloning and parsing to run sandboxed (no execution of repo-provided code, with clone-size and timeout limits, in an isolated filesystem) so a malicious repo cannot compromise the platform.** _(ADR required.)_
- **As a system, I want ingestion and scanning to run as background jobs (Redis-backed queue) so long-running work doesn't block HTTP requests.**
- **As a system, I want every repo and scan associated with an owner (`user_id`) from the start — even using a stub user before login exists — so multi-tenancy doesn't require a painful retrofit later.**
- **As a developer, I want a golden dataset of intentionally-vulnerable sample repos with labeled findings so every detector and (later) eval harness has reference data to validate against.**
- As a user, I want to see a list of files and the detected project type (Docker/Kubernetes/Terraform/etc.) so I understand what will be scanned.
- As a user, I want my Dockerfiles analyzed for common misconfigurations (running as root, missing `USER`, use of `latest` tag, etc.) so I know about container risks. _(Cap: 5 specific checks this sprint.)_
- As a user, I want the Dockerfile findings displayed in the frontend so I can review them without digging through logs.

---

### Sprint 2 — Kubernetes Analysis & Persistence

- As a user, I want my Kubernetes manifests analyzed for common misconfigurations (privileged containers, missing resource limits, `hostNetwork: true`, etc.) so I know about cluster-level risks. _(Cap: 5 specific checks this sprint.)_
- As a system, I want scan results stored in PostgreSQL associated with the repo, owner, and scan run so history is preserved.
- As a system, I want a report generation process that summarizes all findings from a scan run so reports can be produced consistently.
- **As a developer, I want the Sprint 1 detectors validated against the golden dataset in CI so detection accuracy is measured continuously as rules are added.**

---

### Sprint 3 — Reporting UI & Export _(MVP 1 complete)_

- As a user, I want to view my security report in the frontend with findings grouped by severity (high/medium/low) so I can prioritize fixes.
- As a user, I want to export my security report as PDF or Markdown so I can share it outside the platform.
- As a system, I want repo content (code, configs, and scan findings) chunked into retrievable segments so it can later be embedded for RAG.

---

### Sprint 4 — Embeddings & Retrieval

- As a system, I want chunked content converted into embeddings and stored in a vector database (pgvector) so semantic search is possible.
- As a system, I want a retrieval function that, given a natural-language question, returns the most relevant chunks from the vector store so the chatbot can use them as context.
- **As a system, I want LLM/embedding API keys handled as managed secrets, with basic per-request rate and cost controls, so we avoid leaks and surprise bills.**
- As a developer, I want an evaluation script that checks retrieval relevance on the golden dataset so we can verify the pipeline works before building the chatbot on top of it.

_Note: This sprint requires close collaboration between both developers since embeddings and retrieval are tightly coupled — hold the weekly mid-sprint sync._

---

### Sprint 5 — AI Chatbot with Citations _(MVP 2 complete)_

- As a user, I want to ask natural-language questions about my repo's security and get AI-generated answers grounded in retrieved context so I get accurate, relevant guidance.
- As a user, I want to see source citations (file/section) for each chatbot answer so I can verify and trace the information.
- **As a system, I want basic prompt-injection defenses (clear instruction/data separation; treat retrieved repo content as untrusted) so a malicious repo cannot manipulate the assistant's answers.**
- As a developer, I want an evaluation harness comparing chatbot answers against a reference Q&A set so we can measure answer quality over time.

---

### Sprint 6 — Secret Detection & Scan Diffing

- As a user, I want my repository scanned for exposed secrets (API keys, tokens, credentials) using pattern and entropy-based detection so I'm alerted to leaked credentials.
- As a user, I want flagged secrets included in my security report with severity and remediation guidance so I know how to fix them.
- As a user, I want to re-run a scan on my repo and see a diff of findings compared to the previous run so I can track progress over time.

> **Scope note:** Dependency vulnerability scanning (in the original project vision) is intentionally **out of scope** for this build to protect the timeline. Capture it in the long-term extensions backlog.

---

### Sprint 7 — Polish, Auth, Observability & Deployment _(MVP 3 complete)_

- As a user, I want to sign up and log in so my repos and scan history are private to my account. _(Data model already owner-scoped since Sprint 1 — this adds the login UI and real users.)_
- As a user, I want a dashboard summarizing the overall security posture of my repo(s) so I get a quick at-a-glance view.
- **As an operator, I want basic observability (structured logging, a few key metrics, and error alerting) on the deployed app so failures are visible in production.**
- As a developer, I want the application's deployment hardened and documented so it can be demoed reliably without local setup.
- As a developer, I want a complete README and architecture diagram so the project is understandable to new contributors or reviewers.
- As a team, we want to fix outstanding bugs and polish the UI so the demo experience is smooth.