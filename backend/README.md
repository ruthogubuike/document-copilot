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

## Ingest corpus into the database

Load converted markdown filings from `data/markdown/` into `source_documents`:

```bash
uv run python -m ingest.load_source_documents
```

Re-runs skip documents already present (matched by `accession_number`). Set `SKIP_EXISTING = False` in `ingest/load_source_documents.py` to refresh markdown content in place.

## Chunk, embed, and load retrieval passages

Chunk HTML filings with Docling's hybrid chunker, embed with OpenAI, and write `document_chunks`:

```bash
# 1. Verify end-to-end with one chunk (cheap — one embedding API call)
uv run python -m ingest.smoke_test_chunk

# 2. Pilot a single filing
uv run python -m ingest.load_chunks --accession 0000320193-25-000079

# 3. Full corpus (skips documents that already have chunks)
uv run python -m ingest.load_chunks

# Verify ingest + retrieval against client-brief queries
uv run python -m ingest.verify_corpus

# Rebuild chunks for a filing that was already ingested
uv run python -m ingest.load_chunks --accession 0000320193-25-000079 --force-rechunk
```

## Hybrid retrieval (Phase 5)

Search ingested chunks with pgvector + Postgres full-text + RRF fusion:

```bash
# Smoke search from the CLI
uv run python -m app.retrieval.smoke_search "Apple iPhone Services revenue mix"
uv run python -m app.retrieval.smoke_search "NVIDIA Data Center" --ticker NVDA

# Tests
uv run pytest tests/retrieval -m "not integration"
uv run pytest tests/retrieval -m integration   # requires ingested chunks + OpenAI key
```

Requires `source_documents` rows and `data/downloads/` HTML sources. Chunking re-parses HTML into a `DoclingDocument` (native Docling chunkers require structured documents, not markdown alone).

## Grounded chat agent (Phase 6)

`POST /chat/stream` runs a PydanticAI agent with hybrid retrieval tools, validates citations, streams text + `data-citation` parts, and persists `message_citations`.

Config (optional overrides in `.env`):

- `OPENAI_CHAT_MODEL` — default `gpt-4.1-mini`
- `AGENT_MAX_TOOL_CALLS` — default `10`

```bash
# Unit tests (mocked agent, no live OpenAI)
uv run pytest tests/grounding tests/assistant tests/chat -m "not integration"

# Live agent + retrieval (requires ingested chunks + OpenAI key)
uv run pytest tests/chat/test_grounded_integration.py -m integration
```

Live chat verification also needs `document_chunks` from `ingest.load_chunks` before asking filing questions in the UI.

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
