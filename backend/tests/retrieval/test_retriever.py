import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.retrieval.retriever import HybridRetriever
from app.retrieval.types import RetrievedPassage, RetrievalFilters


def _passage(
    chunk_id: uuid.UUID,
    *,
    chunk_index: int = 0,
    ticker: str = "AAPL",
) -> RetrievedPassage:
    return RetrievedPassage(
        chunk_id=chunk_id,
        chunk_index=chunk_index,
        text=f"text for {chunk_id}",
        document_id=uuid.uuid4(),
        ticker=ticker,
        form="10-K",
        fiscal_year=2025,
        filing_date=date(2025, 10, 31),
        accession_number="0000320193-25-000079",
        source_url="https://example.com",
    )


@pytest.mark.asyncio
async def test_retriever_fuses_semantic_and_fulltext_rankings() -> None:
    shared = uuid.uuid4()
    semantic_only = uuid.uuid4()
    fulltext_only = uuid.uuid4()

    passage_map = {
        shared: _passage(shared, chunk_index=1),
        semantic_only: _passage(semantic_only, chunk_index=2),
        fulltext_only: _passage(fulltext_only, chunk_index=4),
    }

    session = AsyncMock()
    retriever = HybridRetriever(candidate_k=10, top_k=2, neighbor_window=0)

    with (
        patch(
            "app.retrieval.retriever.embed_query",
            return_value=[0.1] * 1536,
        ),
        patch(
            "app.retrieval.retriever.semantic_search_ids",
            new=AsyncMock(return_value=[shared, semantic_only]),
        ),
        patch(
            "app.retrieval.retriever.fulltext_search_ids",
            new=AsyncMock(return_value=[shared, fulltext_only]),
        ),
        patch(
            "app.retrieval.retriever.fetch_passages_by_ids",
            new=AsyncMock(return_value=passage_map),
        ),
    ):
        results = await retriever.retrieve(
            session,
            "Apple revenue mix",
            filters=RetrievalFilters(ticker="AAPL"),
        )

    assert len(results) == 2
    assert results[0].chunk_id == shared
    assert results[1].chunk_id in {semantic_only, fulltext_only}


@pytest.mark.asyncio
async def test_retriever_returns_empty_when_both_channels_miss() -> None:
    session = AsyncMock()
    retriever = HybridRetriever()

    with (
        patch("app.retrieval.retriever.embed_query", return_value=[0.1] * 1536),
        patch(
            "app.retrieval.retriever.semantic_search_ids",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.retrieval.retriever.fulltext_search_ids",
            new=AsyncMock(return_value=[]),
        ),
    ):
        results = await retriever.retrieve(session, "nothing here")

    assert results == []
