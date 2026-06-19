from __future__ import annotations

import uuid
from typing import Any

from pydantic_ai import RunContext

from app.assistant.deps import DocumentAgentDeps
from app.retrieval.types import RetrievedPassage, RetrievalFilters

SEARCH_PREVIEW_CHARS = 300


def register_passage(deps: DocumentAgentDeps, passage: RetrievedPassage) -> None:
    deps.retrieved_chunks[passage.chunk_id] = passage
    for neighbor in passage.neighbor_chunks:
        deps.retrieved_chunks[neighbor.chunk_id] = neighbor


def passage_summary(passage: RetrievedPassage) -> dict[str, Any]:
    return {
        "chunk_id": str(passage.chunk_id),
        "ticker": passage.ticker,
        "fiscal_year": passage.fiscal_year,
        "form": passage.form,
        "filing_date": passage.filing_date.isoformat(),
        "section": passage.section,
        "page": passage.page,
        "text_preview": passage.text[:SEARCH_PREVIEW_CHARS],
    }


def passage_detail(passage: RetrievedPassage) -> dict[str, Any]:
    return {
        "chunk_id": str(passage.chunk_id),
        "chunk_index": passage.chunk_index,
        "ticker": passage.ticker,
        "company_name": passage.company_name,
        "fiscal_year": passage.fiscal_year,
        "form": passage.form,
        "filing_date": passage.filing_date.isoformat(),
        "accession_number": passage.accession_number,
        "section": passage.section,
        "page": passage.page,
        "text": passage.text,
    }


async def search_filings(
    ctx: RunContext[DocumentAgentDeps],
    query: str,
    *,
    ticker: str | None = None,
    fiscal_year_min: int | None = None,
    fiscal_year_max: int | None = None,
) -> list[dict[str, Any]]:
    """Search SEC filings for passages relevant to a question."""
    filters = RetrievalFilters(
        ticker=ticker,
        fiscal_year_min=fiscal_year_min,
        fiscal_year_max=fiscal_year_max,
    )
    passages = await ctx.deps.retriever.retrieve(
        ctx.deps.session,
        query,
        filters=filters,
    )
    for passage in passages:
        register_passage(ctx.deps, passage)
    return [passage_summary(passage) for passage in passages]


async def read_chunk(
    ctx: RunContext[DocumentAgentDeps],
    chunk_id: uuid.UUID,
) -> dict[str, Any] | None:
    """Read the full text and metadata for a single chunk."""
    passage = await ctx.deps.retriever.read_chunk(ctx.deps.session, chunk_id)
    if passage is None:
        return None
    register_passage(ctx.deps, passage)
    return passage_detail(passage)


async def read_surrounding_chunks(
    ctx: RunContext[DocumentAgentDeps],
    chunk_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Read a chunk plus neighboring chunks from the same filing."""
    passages = await ctx.deps.retriever.read_surrounding_chunks(
        ctx.deps.session,
        chunk_id,
    )
    for passage in passages:
        register_passage(ctx.deps, passage)
    return [passage_detail(passage) for passage in passages]
