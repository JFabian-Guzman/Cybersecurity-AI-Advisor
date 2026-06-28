# Deployment

The live environment is defined as code in `render.yaml` (a Render Blueprint) and
deployed from version tags via `.github/workflows/deploy.yml`.

## One-time setup

1. Create a Render account and connect this GitHub repository.
2. In Render, choose New > Blueprint and select this repo. Render reads `render.yaml`
   and provisions the Postgres database, the backend (Docker), and the static frontend.
3. During the create flow, Render prompts for the `sync: false` variables:
   - `FRONTEND_ORIGIN` = the frontend URL, e.g. `https://cybersec-frontend.onrender.com`
   - `VITE_API_URL` = the backend URL, e.g. `https://cybersec-backend.onrender.com`
   Render derives URLs from the service names, so these are predictable; confirm the
   exact URLs in the dashboard after the first deploy.
4. In each service's Settings, copy its Deploy Hook URL.
5. In GitHub repo Settings > Secrets and variables > Actions, add:
   - `RENDER_DEPLOY_HOOK_BACKEND`
   - `RENDER_DEPLOY_HOOK_FRONTEND`

## Releasing

Per our GitFlow model, at sprint end merge `develop` into `main`, then tag:

```bash
git checkout main
git pull
git tag v0.1.0
git push origin v0.1.0
```

Pushing the tag runs the Deploy workflow, which calls both Render deploy hooks and
ships the tagged commit. Because the Blueprint sets `autoDeploy: false`, ordinary
pushes to `main` do not deploy.

## Notes

- Free Render services sleep when idle, so the first request after inactivity is slow.
- pgvector is not needed yet; when embeddings land, run `CREATE EXTENSION vector;`
  against the database once.
- To validate the blueprint before pushing: `render blueprints validate`.