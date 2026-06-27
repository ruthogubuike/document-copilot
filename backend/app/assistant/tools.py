from __future__ import annotations

import uuid
from typing import Any

from pydantic_ai import RunContext

from app.assistant.deps import DocumentAgentDeps
from app.retrieval.queries import (
    available_fiscal_years,
    available_tickers,
    count_matching_filings,
)
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


def _describe_period(
    fiscal_year_min: int | None,
    fiscal_year_max: int | None,
) -> str:
    if fiscal_year_min is None and fiscal_year_max is None:
        return "any fiscal year"
    if fiscal_year_min == fiscal_year_max:
        return f"fiscal year {fiscal_year_min}"
    if fiscal_year_min is not None and fiscal_year_max is not None:
        return f"fiscal years {fiscal_year_min}\u2013{fiscal_year_max}"
    if fiscal_year_min is not None:
        return f"fiscal year {fiscal_year_min} or later"
    return f"fiscal year {fiscal_year_max} or earlier"


async def _no_match_response(
    deps: DocumentAgentDeps,
    *,
    ticker: str | None,
    fiscal_year_min: int | None,
    fiscal_year_max: int | None,
) -> dict[str, Any]:
    """Explain an empty search so the model refuses instead of retrying.

    Distinguishes a filing that is genuinely absent from the corpus (refuse, and
    surface the real coverage) from a filing that exists but had no passage match
    the query (report insufficient evidence).
    """
    session = deps.session
    filters = RetrievalFilters(
        ticker=ticker,
        fiscal_year_min=fiscal_year_min,
        fiscal_year_max=fiscal_year_max,
    )
    period = _describe_period(fiscal_year_min, fiscal_year_max)

    if await count_matching_filings(session, filters) > 0:
        return {
            "status": "no_passages_found",
            "message": (
                f"The {ticker or 'requested'} filing for {period} is in the corpus, "
                "but no passage matched this query."
            ),
            "guidance": (
                "Do not invent facts. If the filing genuinely would not address "
                "this, tell the user there is not enough evidence in the corpus to "
                "answer. Rephrase the search at most once before refusing."
            ),
        }

    if ticker is not None and not await available_fiscal_years(session, ticker):
        return {
            "status": "no_matching_filings",
            "message": f"The corpus does not contain any filings for '{ticker}'.",
            "available_tickers": await available_tickers(session),
            "guidance": (
                "Do not retry or broaden the search. Tell the user the corpus does "
                "not contain this company; only the listed companies are available."
            ),
        }

    return {
        "status": "no_matching_filings",
        "message": (
            f"The corpus does not contain a {ticker or 'matching'} filing for "
            f"{period}."
        ),
        "available_fiscal_years": await available_fiscal_years(session, ticker),
        "guidance": (
            "Do not retry with a different year or broaden the search. Tell the user "
            "the corpus does not contain the requested filing; only the listed "
            "fiscal years are available."
        ),
    }


async def search_filings(
    ctx: RunContext[DocumentAgentDeps],
    query: str,
    *,
    ticker: str | None = None,
    fiscal_year: int | None = None,
    fiscal_year_min: int | None = None,
    fiscal_year_max: int | None = None,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Search SEC filings for passages relevant to a question.

    When the question targets one fiscal year, pass `fiscal_year`. If no passage
    matches, this returns an object with a `status` of `no_matching_filings`
    (the filing is not in the corpus) or `no_passages_found` (the filing exists
    but does not address the query) plus the corpus coverage. On either status,
    stop searching and answer from that signal — do not retry to find a filing
    that is not there.
    """
    if fiscal_year is not None:
        fiscal_year_min = fiscal_year
        fiscal_year_max = fiscal_year
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
    if not passages:
        return await _no_match_response(
            ctx.deps,
            ticker=ticker,
            fiscal_year_min=fiscal_year_min,
            fiscal_year_max=fiscal_year_max,
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
