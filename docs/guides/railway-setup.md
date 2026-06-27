# Railway setup (production deploy)

This guide deploys Document Copilot to [Railway](https://railway.com): one **backend** service (FastAPI/Uvicorn) and one **frontend** service (Vite SPA served by `vite preview`), both built from this GitHub monorepo. Supabase stays the database + auth provider; Railway only hosts the two app services.

```text
                 ┌─────────────────────────┐
  browser  ──▶   │ frontend service (Vite)  │  ──▶  backend service (FastAPI)  ──▶  Supabase + OpenAI
                 │ <frontend>.up.railway.app│       <backend>.up.railway.app
                 └─────────────────────────┘
```

Both services live in a single Railway **project**, each pinned to a **root directory** (`backend/` and `frontend/`) of the same repo. Railway reads each service's `railway.json` (build + start config) from that root directory.

## Prerequisites

- A Railway account and workspace (sign in at [railway.com](https://railway.com)).
- The repo pushed to GitHub (`ruthogubuike/document-copilot`), including the deploy config:
  - `backend/railway.json`, `frontend/railway.json`
  - the `start` script in `frontend/package.json` (`vite preview --host 0.0.0.0 --port ${PORT:-4173}`)
  - the `preview` block in `frontend/vite.config.ts`
- A working Supabase project (see [supabase-setup.md](supabase-setup.md)) and an OpenAI API key.
- Your local `backend/.env` filled in — its values are mirrored into Railway.

> The Railway MCP server can do all of this from the agent. The steps below also map 1:1 to the Railway dashboard / `railway` CLI if you'd rather click through.

## Deploy config in the repo

`backend/railway.json` — Railpack build, Uvicorn start, `/health` healthcheck:

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "RAILPACK",
    "watchPatterns": ["app/**", "ingest/**", "pyproject.toml", "uv.lock"]
  },
  "deploy": {
    "startCommand": "uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "restartPolicyType": "ON_FAILURE"
  }
}
```

`frontend/railway.json` — install + build, serve the built SPA with `vite preview`:

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "RAILPACK",
    "buildCommand": "pnpm install --frozen-lockfile && pnpm build",
    "watchPatterns": ["src/**", "public/**", "index.html", "package.json", "pnpm-lock.yaml"]
  },
  "deploy": {
    "startCommand": "pnpm start",
    "restartPolicyType": "ON_FAILURE"
  }
}
```

Railway injects `$PORT` at runtime; both services bind to it (`--port $PORT` for Uvicorn, `${PORT}` via the `preview` block for Vite). Don't hardcode a port.

## Step 1 — Create the project

Create a Railway project (e.g. `document-copilot`) in your workspace. It comes with a default `production` environment.

## Step 2 — Create the two services

Create both services in the project from the GitHub repo, then pin each to its subdirectory:

| Service | Source repo | Branch | Root directory |
| ------- | ----------- | ------ | -------------- |
| `backend` | `ruthogubuike/document-copilot` | `main` | `backend` |
| `frontend` | `ruthogubuike/document-copilot` | `main` | `frontend` |

Setting the **root directory** is what makes the monorepo work: Railway builds each service from its own folder and reads that folder's `railway.json`.

> If Railway can't see the repo, install the [Railway GitHub App](https://railway.com/account) on `ruthogubuike/document-copilot` and reconnect. Without it, services can still be deployed by uploading the directory, but you lose auto-deploy on push.

## Step 3 — Generate public domains

Generate a Railway domain for each service. You'll get URLs like:

- backend: `https://<backend>.up.railway.app`
- frontend: `https://<frontend>.up.railway.app`

You need both before setting variables, because the two services reference each other (CORS + API base URL).

## Step 4 — Set environment variables

### Backend service

Mirror `backend/.env`, but point `ALLOWED_ORIGINS` at the **frontend** Railway domain (no trailing slash). Only these are required (the rest have defaults in `app/config.py`):

| Variable | Value |
| -------- | ----- |
| `SUPABASE_URL` | from Supabase |
| `SUPABASE_ANON_KEY` | from Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | from Supabase |
| `DATABASE_URL` | Supabase Postgres connection string |
| `OPENAI_API_KEY` | from OpenAI |
| `ALLOWED_ORIGINS` | `https://<frontend>.up.railway.app` |

Optional overrides (defaults shown): `OPENAI_EMBEDDING_MODEL=text-embedding-3-small`, `OPENAI_EMBEDDING_DIMENSIONS=1536`, `OPENAI_CHAT_MODEL=gpt-4.1-mini`, `AGENT_MAX_TOOL_CALLS=20`.

### Frontend service

`VITE_*` vars are read at **build time**, so they must be set before the build runs. Point `VITE_API_BASE_URL` at the **backend** Railway domain:

| Variable | Value |
| -------- | ----- |
| `VITE_API_BASE_URL` | `https://<backend>.up.railway.app` |
| `VITE_SUPABASE_URL` | same as backend `SUPABASE_URL` |
| `VITE_SUPABASE_ANON_KEY` | same as backend `SUPABASE_ANON_KEY` |

Changing a `VITE_*` var requires a **redeploy** to take effect (it's baked into the static bundle).

## Step 5 — Database migrations & corpus

Railway hosts the app only; the schema and corpus live in Supabase. Run these once against the production database from your machine (use the **direct** connection, not the transaction pooler, for Alembic):

```powershell
cd backend
uv run alembic upgrade head
uv run python -m ingest.load_source_documents
uv run python -m ingest.load_chunks
uv run python -m ingest.verify_corpus
```

## Step 6 — Verify

1. Backend health: open `https://<backend>.up.railway.app/health` → `200`.
2. Frontend: open `https://<frontend>.up.railway.app`, sign in, send a question, confirm a grounded answer with citations.
3. If the browser console shows CORS errors, re-check `ALLOWED_ORIGINS` on the backend matches the frontend origin exactly (scheme + host, no trailing slash), then redeploy the backend.

## Continuous deploys

With the GitHub App connected and root directories set, pushing to `main` triggers a rebuild of whichever service's `watchPatterns` changed. Backend redeploys are zero-touch; for frontend changes to `VITE_*` values (not code), trigger a redeploy so the new value is baked in.

## Troubleshooting

| Symptom | Likely cause | Fix |
| ------- | ------------ | --- |
| Frontend build fails on `pnpm` | lockfile out of date | run `pnpm install` locally, commit `pnpm-lock.yaml`, push |
| `vite preview` returns "host not allowed" | preview host check | the `preview.host: true` block in `vite.config.ts` must be deployed |
| Backend boots then crashes | missing required env var | check deploy logs; set the missing `SUPABASE_*` / `DATABASE_URL` / `OPENAI_API_KEY` |
| 401/empty data in app | `VITE_*` baked at build time were wrong | fix vars, redeploy frontend |
| CORS error in browser | `ALLOWED_ORIGINS` mismatch | set it to the exact frontend origin, redeploy backend |
| Migrations hang/timeout | using the transaction pooler URL | use the direct `db.<ref>.supabase.co` connection for Alembic |
