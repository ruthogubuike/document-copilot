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


_REFUSAL_PHRASES = (
    "evidence",
    "corpus",
    "do not contain",
    "does not contain",
    "not disclosed",
    "not stated",
    "not available",
)


async def _run_turn(query: str):
    from pydantic_ai.usage import UsageLimits

    from app.assistant.agent import document_agent
    from app.assistant.deps import DocumentAgentDeps
    from app.config import settings
    from app.database.session import get_async_session
    from app.retrieval.retriever import HybridRetriever

    async with get_async_session() as session:
        deps = DocumentAgentDeps(
            retriever=HybridRetriever(),
            session=session,
            retrieved_chunks={},
        )
        result = await document_agent.run(
            query,
            deps=deps,
            # Mirror production so a looping agent fails loudly instead of refusing.
            usage_limits=UsageLimits(tool_calls_limit=settings.agent_max_tool_calls),
        )
    return result.output, deps


@pytest.mark.integration
@pytest.mark.asyncio
async def test_grounded_turn_insufficient_evidence_without_corpus_match() -> None:
    _require_ingested_chunks()
    from app.grounding.validator import validate_grounded_answer

    output, deps = await _run_turn(
        "What is Apple's official stock price target for 2030?"
    )

    validate_grounded_answer(output, deps.retrieved_chunks)
    assert not output.citations
    assert any(phrase in output.answer.lower() for phrase in _REFUSAL_PHRASES)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_grounded_turn_refuses_out_of_range_past_year() -> None:
    """A real past-year filing (Apple 2018) is outside the corpus; refuse, don't loop."""
    _require_ingested_chunks()
    from app.grounding.validator import validate_grounded_answer

    output, deps = await _run_turn(
        "What did Apple's 2018 10-K list as its top risk factors?"
    )

    validate_grounded_answer(output, deps.retrieved_chunks)
    assert not output.citations
    assert any(phrase in output.answer.lower() for phrase in _REFUSAL_PHRASES)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_grounded_turn_refuses_company_absent_from_corpus() -> None:
    _require_ingested_chunks()
    from app.grounding.validator import validate_grounded_answer

    output, deps = await _run_turn(
        "What does Tesla's latest 10-K say about automotive gross margin?"
    )

    validate_grounded_answer(output, deps.retrieved_chunks)
    assert not output.citations
    assert any(phrase in output.answer.lower() for phrase in _REFUSAL_PHRASES)
