from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai import RunContext

from app.assistant import tools
from app.assistant.deps import DocumentAgentDeps
from app.assistant.tools import read_chunk, read_surrounding_chunks, register_passage, search_filings
from app.retrieval.retriever import HybridRetriever
from app.retrieval.types import RetrievedPassage, RetrievalFilters


def _passage(chunk_id: uuid.UUID | None = None) -> RetrievedPassage:
    return RetrievedPassage(
        chunk_id=chunk_id or uuid.uuid4(),
        chunk_index=1,
        text="AWS operating income increased.",
        document_id=uuid.uuid4(),
        ticker="AMZN",
        form="10-K",
        fiscal_year=2024,
        filing_date=date(2024, 2, 2),
        accession_number="0001018724-24-000008",
        source_url="https://example.com",
    )


def _run_context(deps: DocumentAgentDeps) -> RunContext[DocumentAgentDeps]:
    return RunContext(
        deps=deps,
        model=MagicMock(),
        usage=MagicMock(),
        prompt="test",
        run_id=str(uuid.uuid4()),
    )


@pytest.mark.asyncio
async def test_search_filings_registers_chunks_and_passes_filters() -> None:
    passage = _passage()
    retriever = MagicMock(spec=HybridRetriever)
    retriever.retrieve = AsyncMock(return_value=[passage])
    session = AsyncMock()
    deps = DocumentAgentDeps(retriever=retriever, session=session)
    ctx = _run_context(deps)

    results = await search_filings(
        ctx,
        "AWS operating income",
        ticker="AMZN",
        fiscal_year_min=2021,
        fiscal_year_max=2025,
    )

    retriever.retrieve.assert_awaited_once()
    call_kwargs = retriever.retrieve.await_args.kwargs
    assert call_kwargs["filters"] == RetrievalFilters(
        ticker="AMZN",
        fiscal_year_min=2021,
        fiscal_year_max=2025,
    )
    assert passage.chunk_id in deps.retrieved_chunks
    assert results[0]["ticker"] == "AMZN"


@pytest.mark.asyncio
async def test_search_filings_fiscal_year_sets_exact_range() -> None:
    passage = _passage()
    retriever = MagicMock(spec=HybridRetriever)
    retriever.retrieve = AsyncMock(return_value=[passage])
    deps = DocumentAgentDeps(retriever=retriever, session=AsyncMock())
    ctx = _run_context(deps)

    await search_filings(ctx, "iPhone revenue", ticker="AAPL", fiscal_year=2027)

    call_kwargs = retriever.retrieve.await_args.kwargs
    assert call_kwargs["filters"] == RetrievalFilters(
        ticker="AAPL",
        fiscal_year_min=2027,
        fiscal_year_max=2027,
    )


@pytest.mark.asyncio
async def test_search_filings_reports_company_absent_from_corpus(monkeypatch) -> None:
    retriever = MagicMock(spec=HybridRetriever)
    retriever.retrieve = AsyncMock(return_value=[])
    deps = DocumentAgentDeps(retriever=retriever, session=AsyncMock())
    ctx = _run_context(deps)

    monkeypatch.setattr(tools, "count_matching_filings", AsyncMock(return_value=0))
    monkeypatch.setattr(tools, "available_fiscal_years", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        tools, "available_tickers", AsyncMock(return_value=["AAPL", "AMZN"])
    )

    result = await search_filings(ctx, "risk factors", ticker="TSLA")

    assert isinstance(result, dict)
    assert result["status"] == "no_matching_filings"
    assert result["available_tickers"] == ["AAPL", "AMZN"]
    assert deps.retrieved_chunks == {}


@pytest.mark.asyncio
async def test_search_filings_reports_period_out_of_range(monkeypatch) -> None:
    retriever = MagicMock(spec=HybridRetriever)
    retriever.retrieve = AsyncMock(return_value=[])
    deps = DocumentAgentDeps(retriever=retriever, session=AsyncMock())
    ctx = _run_context(deps)

    monkeypatch.setattr(tools, "count_matching_filings", AsyncMock(return_value=0))
    monkeypatch.setattr(
        tools,
        "available_fiscal_years",
        AsyncMock(return_value=[2021, 2022, 2023, 2024, 2025]),
    )

    result = await search_filings(ctx, "risk factors", ticker="AAPL", fiscal_year=2018)

    assert isinstance(result, dict)
    assert result["status"] == "no_matching_filings"
    assert result["available_fiscal_years"] == [2021, 2022, 2023, 2024, 2025]
    assert "2018" in result["message"]


@pytest.mark.asyncio
async def test_search_filings_reports_filing_present_but_no_passage(monkeypatch) -> None:
    retriever = MagicMock(spec=HybridRetriever)
    retriever.retrieve = AsyncMock(return_value=[])
    deps = DocumentAgentDeps(retriever=retriever, session=AsyncMock())
    ctx = _run_context(deps)

    monkeypatch.setattr(tools, "count_matching_filings", AsyncMock(return_value=1))

    result = await search_filings(ctx, "obscure metric", ticker="AAPL", fiscal_year=2024)

    assert isinstance(result, dict)
    assert result["status"] == "no_passages_found"


@pytest.mark.asyncio
async def test_read_chunk_registers_passage() -> None:
    passage = _passage()
    retriever = MagicMock(spec=HybridRetriever)
    retriever.read_chunk = AsyncMock(return_value=passage)
    deps = DocumentAgentDeps(retriever=retriever, session=AsyncMock())
    ctx = _run_context(deps)

    result = await read_chunk(ctx, passage.chunk_id)

    assert result is not None
    assert result["chunk_id"] == str(passage.chunk_id)
    assert deps.retrieved_chunks[passage.chunk_id] == passage


@pytest.mark.asyncio
async def test_read_surrounding_chunks_registers_all_passages() -> None:
    center = _passage()
    neighbor = _passage()
    retriever = MagicMock(spec=HybridRetriever)
    retriever.read_surrounding_chunks = AsyncMock(return_value=[center, neighbor])
    deps = DocumentAgentDeps(retriever=retriever, session=AsyncMock())
    ctx = _run_context(deps)

    results = await read_surrounding_chunks(ctx, center.chunk_id)

    assert len(results) == 2
    assert center.chunk_id in deps.retrieved_chunks
    assert neighbor.chunk_id in deps.retrieved_chunks


def test_register_passage_includes_neighbors() -> None:
    neighbor = _passage()
    center = _passage().model_copy(update={"neighbor_chunks": [neighbor]})
    deps = DocumentAgentDeps(retriever=MagicMock(), session=AsyncMock())

    register_passage(deps, center)

    assert center.chunk_id in deps.retrieved_chunks
    assert neighbor.chunk_id in deps.retrieved_chunks
