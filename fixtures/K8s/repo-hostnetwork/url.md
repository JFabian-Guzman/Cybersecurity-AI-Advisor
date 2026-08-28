# Real-world Repo Reference

This fixture targets manifests that set `hostNetwork`, `hostPID`, or
`hostIPC` to `true` (K8S002).

## Suggested repos

| Repo | Reason |
|------|--------|
| [BishopFox/badPods](https://github.com/BishopFox/badPods) | Collection of intentionally vulnerable Kubernetes Pod manifests for privilege-escalation training, including examples that set `hostNetwork`/`hostPID`/`hostIPC: true`. |

### Clone URLs

- **HTTPS:** `https://github.com/BishopFox/badPods.git`
- **SSH:** `git@github.com:BishopFox/badPods.git`