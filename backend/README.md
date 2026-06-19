# Document Copilot — Backend

FastAPI service for auth, chat, retrieval, and grounded answers over SEC filings.

**Requires:** Python 3.12+, [uv](https://docs.astral.sh/uv/)

## First-time setup

```bash
cd backend
cp .env.example .env   # fill in Supabase, Postgres, and OpenAI values
uv sync
```

All configuration lives in `app/config.py` (loaded from `.env`). The app fails on startup if required variables are missing.

## Run the API

```bash
cd backend
uv run uvicorn app.main:app --reload
```

Or:

```bash
uv run python app/main.py
```

- API: http://127.0.0.1:8000
- Health check: http://127.0.0.1:8000/health
- OpenAPI docs: http://127.0.0.1:8000/docs

`uv run` uses the project venv automatically. To activate it manually (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

## Database migrations

Once Alembic is configured:

```bash
uv run alembic upgrade head          # apply migrations
uv run alembic revision --autogenerate -m "describe change"   # after model changes
```

Use the **direct** Supabase Postgres connection string in `DATABASE_URL`, not the transaction pooler.

## Tests and lint

```bash
uv run pytest
uv run pytest -m "not integration"   # unit tests only (no live DB/API)
uv run ruff check .
```

## Project layout

```text
backend/
├── app/
│   ├── config.py    # env settings (single source of truth)
│   └── main.py      # FastAPI app entrypoint
├── alembic/         # migrations (when added)
└── tests/
```

Imports use the installed package: `from app.config import settings`. See [docs/guides/backend-setup.md](../docs/guides/backend-setup.md) for more detail.
