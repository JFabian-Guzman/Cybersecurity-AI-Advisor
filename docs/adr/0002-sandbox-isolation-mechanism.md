# 0002. Sandbox isolation mechanism for repository cloning and parsing

- Status: accepted
- Date: 2026-06-29
- Deciders: Dev A

## Context

The platform clones and parses arbitrary third-party repositories submitted by users.
These repositories are untrusted and may contain malicious content designed to compromise
the host system — for example, Git checkout hooks that execute shell commands, zip bombs,
path traversal archives, or build scripts that exfiltrate environment variables.

Cloning and parsing must therefore run in an isolated environment with:
- No access to the host filesystem beyond the designated clone directory
- No network access during analysis (prevents SSRF and data exfiltration)
- Strict CPU, memory, and wall-clock time limits
- No execution of repo-provided hooks or scripts
- A clean, ephemeral filesystem per scan that is discarded after use

The project already runs on Docker (local dev via docker-compose, production via Render).
The team is two people working part-time on a portfolio project, so operational complexity
is a hard constraint.

## Decision

We will use an **ephemeral hardened Docker container per scan** as the sandbox mechanism.

The worker process spawns a new container for each scan job using the Docker SDK for Python
(`docker` library). The container is built from `backend/sandbox/Dockerfile`, which runs as
a non-root user with a read-only filesystem, no network, strict resource limits, and no
new-privilege escalation. The worker passes the repository URL or archive path to the
container via environment variables, mounts a tmpfs volume for the clone output, and reads
the structured findings from stdout after the container exits. The container is removed
immediately after the job completes or times out.

Git hooks are neutralized by cloning with `--no-checkout` followed by a controlled
checkout using `GIT_CONFIG_NOSYSTEM=1` and `core.hooksPath=/dev/null`.

Clone size and timeout limits are configurable via `SANDBOX_MAX_CLONE_MB` and
`SANDBOX_TIMEOUT_SECONDS` environment variables.

## Consequences

### Positive

- No new infrastructure required — Docker is already the deployment primitive.
- The sandbox image is independently versioned and upgradeable without touching the worker.
- Container-level resource limits (CPU, memory, PIDs) are enforced by the Docker daemon,
  not by application code, making them harder to bypass.
- The worker never touches untrusted bytes directly — only structured output crosses the
  boundary.
- Ephemeral containers leave no residue between scans.

### Negative

- Requires the Docker socket to be accessible from the worker container, which grants
  significant host privilege. This is an accepted risk for a portfolio deployment on Render;
  a production hardening step would be to use a rootless Docker daemon or replace the
  docker.sock mount with a dedicated container runtime API.
- Spawning a container per scan adds latency (~1–2s overhead) compared to in-process
  execution. Acceptable for the current scan volumes.
- Local development requires Docker Desktop to be running, which is already a prerequisite.

## Alternatives considered

- **bubblewrap / nsjail**: Provides strong Linux namespace isolation without requiring
  Docker. Rejected because it requires kernel features that may not be available on
  Render's managed infrastructure, and adds operational complexity for a two-person team.
- **gVisor (runsc)**: Strongest isolation with a user-space kernel. Rejected because it
  requires a custom Docker runtime configured at the host level, which is not available on
  Render's free tier.
- **In-process sandboxing (RestrictedPython, etc.)**: Insufficient — Python-level
  sandboxes cannot prevent syscall-level attacks and do not provide filesystem or network
  isolation.