"""Integration tests for grounded chat turns (requires ingested chunks + OpenAI)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, func, select

from app.config import settings
from app.database.models import DocumentChunk


def _require_ingested_chunks() -> None:
    engine = create_engine(settings.sqlalchemy_database_url)
    with engine.connect() as connection:
        count = connection.execute(
            select(func.count()).select_from(DocumentChunk)
        ).scalar_one()
    if count == 0:
        pytest.skip("No document_chunks in database — run ingest.load_chunks first")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_grounded_turn_insufficient_evidence_without_corpus_match() -> None:
    _require_ingested_chunks()

    from app.assistant.agent import document_agent
    from app.assistant.deps import DocumentAgentDeps
    from app.database.session import get_async_session
    from app.grounding.validator import validate_grounded_answer
    from app.retrieval.retriever import HybridRetriever

    query = "What is Apple's official stock price target for 2030?"

    async with get_async_session() as session:
        deps = DocumentAgentDeps(
            retriever=HybridRetriever(),
            session=session,
            retrieved_chunks={},
        )
        result = await document_agent.run(
            query,
            deps=deps,
        )

    output = result.output
    validate_grounded_answer(output, deps.retrieved_chunks)
    assert not output.citations
    answer = output.answer.lower()
    assert any(
        phrase in answer
        for phrase in (
            "evidence",
            "corpus",
            "do not contain",
            "does not contain",
            "not disclosed",
            "not stated",
        )
    )
