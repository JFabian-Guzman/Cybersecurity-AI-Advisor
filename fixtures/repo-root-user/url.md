# Real-world Repo Reference

This fixture targets real repositories whose Dockerfiles lack a `USER` directive,
causing the container to run as root (DF001).

## Suggested repos

| Repo | Reason |
|------|--------|
| [SamP10/VulnerableDockerfile](https://github.com/SamP10/VulnerableDockerfile) | Intentionally vulnerable Dockerfile — no USER directive, runs as root |
| [ianmiell/bad-dockerfile](https://github.com/ianmiell/bad-dockerfile) | Reference Dockerfile with known vulnerabilities, no USER set |
