import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import DocumentChunk
from app.database.session import get_async_session
from app.retrieval.retriever import HybridRetriever
from app.retrieval.types import RetrievalFilters


def _require_ingested_chunks() -> None:
    engine = create_engine(settings.sqlalchemy_database_url)
    with Session(engine) as session:
        count = session.scalar(select(func.count()).select_from(DocumentChunk))
    if not count:
        pytest.skip("No document_chunks ingested yet — run ingest.load_chunks first")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_hybrid_retrieval_returns_aapl_passages() -> None:
    _require_ingested_chunks()

    retriever = HybridRetriever(top_k=5)
    async with get_async_session() as session:
        passages = await retriever.retrieve(
            session,
            "Apple iPhone Services revenue mix",
            filters=RetrievalFilters(ticker="AAPL"),
        )

    assert passages
    assert all(passage.ticker == "AAPL" for passage in passages)
    assert all(passage.text.strip() for passage in passages)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_hybrid_retrieval_cross_ticker_query() -> None:
    _require_ingested_chunks()

    retriever = HybridRetriever(top_k=5)
    async with get_async_session() as session:
        passages = await retriever.retrieve(
            session,
            "NVIDIA Data Center demand drivers",
            filters=RetrievalFilters(ticker="NVDA"),
        )

    assert passages
    assert all(passage.ticker == "NVDA" for passage in passages)
