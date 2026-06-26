# Document Copilot — implementation checklist

Work top to bottom. Each phase unlocks the next. Check items off as you go.

## Current status

**Phases 1–7 complete** for the sample corpus. Full ingest: 25 filings, 419 `document_chunks`. Phase 8 (pilot readiness) is next.

| Phase | Status | Notes |
| ----- | ------ | ----- |
| 0 — Prerequisites | Done | Corpus downloaded; toolchain + Supabase in active use |
| 1 — Backend scaffold & DB | Done | Schema migrated, health + Supabase clients |
| 2 — Auth | Done | Email auth full stack |
| 3 — Chat shell | Done | Thread CRUD, AI SDK streaming, sidebar + messages |
| 4 — Ingestion | Done | 25 `source_documents`, 419 `document_chunks`, embeddings + `tsvector` verified |
| 5 — Retrieval | Done | Hybrid search verified via `ingest.verify_corpus` + integration tests |
| 6 — LLM agent & grounding | Done | Grounded chat + citation persistence; manual + integration verify |
| 7 — Trust UI | Done | Citation chips, source panel, empty/error states |
| 8 — Pilot readiness | Not started | |
| 9 — Deployment | Not started | |

### Backend (`backend/app/`)

- `GET /health`, `GET /me` — health + auth smoke test
- `GET/POST /chat/threads`, `GET /chat/threads/{id}/messages` — thread CRUD (Supabase client + RLS)
- `POST /chat/stream` — PydanticAI grounded agent; streams text + `data-citation` parts; persists messages + citations
- `app/database/chats.py`, `app/database/users.py`, `app/chat/access.py` — persistence + 403/404 guards
- `tests/chat/` — messages, access, streaming, API, orchestrator, grounding integration
- `ingest/` — `load_source_documents`, `load_chunks`, `smoke_test_chunk`, Docling hybrid chunking + OpenAI embeddings
- `tests/ingest/` — manifest, chunking, and embedding unit tests
- `app/retrieval/` — `HybridRetriever` (pgvector + FTS + RRF)
- `app/assistant/` — PydanticAI agent, tools, `GroundedAnswer` output, instructions
- `app/grounding/` — citation validation (fail closed)
- `tests/retrieval/` — fusion, retriever mocks, integration tests

### Frontend (`frontend/src/`)

- Routes: `/login`, `/signup`, `/` → `/chat`, `/chat/:threadId`
- `ai` + `@ai-sdk/react` `useChat` with `DefaultChatTransport` → `POST /chat/stream`
- Sidebar (thread list, new chat, sign out), message list, input, streaming indicator
- Citation chips on assistant messages; right-side source passage panel (Sheet)
- Corpus-aware empty states, typed error banners, submitted/streaming status labels
- `pnpm build` and `pnpm tsc --noEmit` pass

**Next:** Phase 8 — pilot readiness (local runbook, logging, smoke tests).

---

## Where to start: backend, frontend, or both?

**Start with foundation, then backend-led vertical slices.**


| Order                             | Why                                                                                                                    |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| 1. Supabase + sample data         | Everything persists here; you need a project and a corpus to test against.                                             |
| 2. Backend schema + migrations    | Auth, chat, retrieval, and citations all depend on the data model.                                                     |
| 3. Thin vertical slices           | Wire auth, then a stubbed chat stream, then real RAG — each slice touches frontend + backend together.                 |
| 4. Frontend in parallel (lightly) | Scaffold the SPA early, but don't build citation UI or chat polish until the backend can return real grounded answers. |


The critical path is **data model → ingestion → retrieval → LLM → citations**. The frontend is mostly a streaming chat shell with auth and citation display — it shouldn't get far ahead of working APIs.

---

## Phase 0 — Prerequisites & foundation

- [x] Install toolchain: Python 3.12+, `uv`, Node 20+, `pnpm` (see [README](../README.md))
- [x] Create Supabase project and collect credentials ([supabase-setup](guides/supabase-setup.md))

- [x] Create OpenAI API key (needed from Phase 6 onward)
- [x] Set `USER_AGENT` in `data/download.py` and download sample 10-K corpus:
  ```bash
  uv run data/download.py
  ```
- [x] Confirm `data/downloads/manifest.json` lists AAPL, MSFT, NVDA, AMZN, GOOGL filings (2021–2025)

---

## Phase 1 — Backend scaffold & database

Goal: a running FastAPI service with a migrated Supabase schema.

- [x] Init backend deps and project layout ([backend-setup](guides/backend-setup.md))
- [x] `app/config.py` — settings module, fail fast on missing env vars
- [x] `app/main.py` — FastAPI app, CORS, health check (`GET /health`)
- [x] SQLAlchemy models in `app/database/models/`:
  - [x] `users`
  - [x] `source_documents`
  - [x] `document_chunks` (embedding + generated `tsvector`)
  - [x] `chat_threads`
  - [x] `chat_messages`
  - [x] `message_citations`
- [x] Alembic init + first migration:
  - [x] `create extension if not exists vector`
  - [x] `vector(1536)` embedding column
  - [x] generated `tsvector` column on chunks
  - [x] HNSW index (vector) + GIN index (full-text)
  - [x] RLS policies (users see only their own chats)
- [x] `uv run alembic upgrade head` against Supabase direct connection
- [x] `app/database/supabase.py` — user-scoped and service-role clients
- [x] Verify: `uv run uvicorn app.main:app --reload` → health check returns 200

---

## Phase 2 — Auth (full stack)

Goal: analysts can sign in with email; backend rejects unauthenticated requests.

**Backend**

- [x] `app/auth/dependencies.py` — verify `Authorization: Bearer <supabase_jwt>`, expose `get_current_user`
- [x] Reject missing/expired tokens with `401` before any chat or retrieval work

**Frontend**

- [x] Scaffold Vite + React + TypeScript + Tailwind + shadcn ([frontend-setup](guides/frontend-setup.md))
- [x] `src/lib/env.ts` — validate `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- [x] `src/lib/supabase.ts` — browser Supabase client
- [x] `src/lib/http.ts` + `src/lib/api.ts` — fetch wrapper with automatic bearer token
- [x] Sign-in / sign-up pages (email only, no SSO)
- [x] Protected routes — redirect unauthenticated users to login
- [x] Verify: sign up, sign in, token reaches backend on a test authenticated endpoint

---

## Phase 3 — Chat shell (vertical slice, stubbed)

Goal: end-to-end chat UI streaming from FastAPI, no real retrieval yet.

**Backend**

- [x] Chat thread CRUD: `GET/POST /chat/threads`, `GET /chat/threads/{id}/messages`
- [x] `POST /chat/stream` — accepts AI SDK message format, streams a stubbed assistant reply
- [x] Persist user + assistant messages to `chat_messages` after stream completes
- [x] `403` when user accesses another user's thread (`app/chat/access.py`)
- [x] Unit tests: `tests/chat/` (15 tests)

**Frontend**

- [x] React Router: `/login`, `/signup`, `/chat`, `/chat/:threadId` (`/` redirects to `/chat`)
- [x] AI SDK chat primitives pointed at `POST /chat/stream` with Supabase bearer token
- [x] Thread sidebar (past conversations)
- [x] Basic message list + input + streaming indicator
- [x] Verify: create thread, send message, see streamed stub response, reload and see history

---

## Phase 4 — Ingestion pipeline

Goal: SEC filings in the corpus are parsed, chunked, embedded, and stored in Supabase.

- [x] `ingest/` scripts (or CLI entrypoint) for one-off corpus loading
- [x] HTML → normalized Markdown extraction (`data/convert_to_markdown.py`; page/section metadata richer at Docling chunk time from HTML)
- [x] Chunking strategy (Docling `HybridChunker` + hierarchical base; chunk index, page, section, ticker, filing type, year in `chunk_metadata`)
- [x] Write `source_documents` rows with filing metadata from `manifest.json`
- [x] Write `document_chunks` rows with text + metadata
- [x] OpenAI embedding generation → store `vector(1536)` per chunk
- [x] Generated `tsvector` populated for full-text search (auto via DB; verify after chunks land)
- [x] Idempotent re-run (skip already-ingested documents)
- [x] Unit tests: chunking logic, metadata extraction
- [x] Run ingestion on full sample corpus (25 filings × 5 companies)
- [x] Verify: chunks exist in Supabase; spot-check a known passage (e.g. Apple revenue mix table)

---

## Phase 5 — Retrieval

Goal: a user question returns ranked, relevant source passages.

- [x] `retrieval/queries.py` — pgvector semantic search over `document_chunks`
- [x] `retrieval/queries.py` — Postgres full-text search over `search_vector`
- [x] `retrieval/fusion.py` — Reciprocal Rank Fusion in Python
- [x] `retrieval/retriever.py` — query → fused ranked passages + neighbor chunks
- [x] Unit tests: fusion ranking, query assembly (mock DB)
- [x] Integration test (optional, `@pytest.mark.integration`): real query against ingested corpus
- [x] Verify: test queries from [client-brief](client-brief.md) return relevant chunks (`ingest.verify_corpus`)

---

## Phase 6 — LLM agent & grounding

Goal: grounded answers with enforced citations — the core product contract.

- [x] `assistant/instructions.md` — product contract (cite everything, refuse to invent, no stock picks)
- [x] PydanticAI agent with typed deps (`DocumentAgentDeps`) and output (`GroundedAnswer`)
- [x] Agent tools: `search_filings`, `read_chunk`, `read_surrounding_chunks`
- [x] `chat/orchestrator.py` — one turn: retrieve → agent → validate → stream → persist
- [x] `grounding/validator.py` — every citation maps to a retrieved passage; fail closed on violation
- [x] `chat/streaming.py` — citation metadata parts in stream
- [x] Persist `message_citations` linked to assistant messages
- [x] Unit tests: citation validation, grounding enforcement, message conversion
- [x] Verify against [client-brief example questions](client-brief.md#example-analyst-questions):
  - [x] Answers cite specific filings and pages (manual chat test: iPhone revenue)
  - [x] Under-specified questions get "not enough evidence" responses (manual: stock price target)
  - [x] Question 10 (generative AI margins) refuses to infer beyond filings (manual + agent instructions)

---

## Phase 7 — Trust UI (citations & source passages)

Goal: analysts can verify every claim in one click — this is what makes the product usable.

> Phase 3 shipped a basic streaming indicator and minimal error display. Citation UI and corpus-aware empty/error states are still out of scope.

- [x] Citation chips/links on assistant messages (company, filing type, date, page/section)
- [x] Source passage panel — show underlying excerpt for selected citation
- [x] Empty states (no threads, no corpus match)
- [x] Error states (auth expired, retrieval failure, grounding failure, network/CORS)
- [x] Loading/streaming status during assistant run
- [x] Verify: click a citation → see the exact passage from the filing

---

## Phase 8 — Pilot readiness

Goal: 5 senior analysts can use it for a week and report ≥3 hours saved per analyst per week.

- [ ] README "Running locally" section — copy-paste commands for backend + frontend + env vars
- [ ] Seed or document how to ingest/update the corpus
- [ ] Smoke-test all 10 example questions from the client brief
- [x] Confirm chat history persists across sessions (Phase 3 vertical slice)
- [ ] Confirm ~40-user scale assumptions (no hardcoded single-user shortcuts)
- [ ] Basic structured logging on backend (`structlog`) for debugging failed turns
- [ ] Review latency: streaming starts within a few seconds for typical queries

---

## Phase 9 — Deployment (Railway)

- [ ] Railway: backend service (Uvicorn, env vars, `ALLOWED_ORIGINS`)
- [ ] Railway: frontend service (Vite build, `VITE_`* env vars at build time)
- [ ] Supabase: re-enable email confirmation for production if disabled during dev
- [ ] Run `alembic upgrade head` against production Supabase (direct connection)
- [ ] Run ingestion against production database
- [ ] End-to-end test on deployed URLs with a real Driftwood-style email account

---

## Quick reference


| Doc                                                  | Purpose                                       |
| ---------------------------------------------------- | --------------------------------------------- |
| [client-brief.md](client-brief.md)                   | What Driftwood needs and example questions    |
| [architecture.md](architecture.md)                   | System design, data model, streaming contract |
| [guides/supabase-setup.md](guides/supabase-setup.md) | Hosted Postgres + Auth                        |
| [guides/backend-setup.md](guides/backend-setup.md)   | FastAPI + Alembic commands                    |
| [guides/frontend-setup.md](guides/frontend-setup.md) | Vite + React scaffold commands                |


