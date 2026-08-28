# Real-world Repo Reference

This fixture targets manifests that run a container with
`securityContext.privileged: true` (K8S001).

## Suggested repos

| Repo | Reason |
|------|--------|
| [moby/buildkit](https://github.com/moby/buildkit/blob/master/examples/kubernetes/statefulset.privileged.yaml) | Example `StatefulSet` manifest running BuildKit workers with `securityContext.privileged: true`, required for its container-building workload. |

### Clone URLs

- **HTTPS:** `https://github.com/moby/buildkit.git`
- **SSH:** `git@github.com:moby/buildkit.git`