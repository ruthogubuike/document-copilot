from __future__ import annotations

import uuid
from datetime import date

from app.assistant.outputs import Citation, GroundedAnswer
from app.grounding.normalize import normalize_grounded_answer
from app.grounding.validator import GroundingError, validate_grounded_answer
from app.retrieval.types import RetrievedPassage


def _passage(chunk_id: uuid.UUID, text: str) -> RetrievedPassage:
    return RetrievedPassage(
        chunk_id=chunk_id,
        chunk_index=0,
        text=text,
        document_id=uuid.uuid4(),
        ticker="AAPL",
        form="10-K",
        fiscal_year=2025,
        filing_date=date(2025, 10, 31),
        accession_number="0000320193-25-000079",
        source_url="https://example.com",
    )


def test_normalize_replaces_non_matching_excerpt_with_chunk_fallback() -> None:
    chunk_id = uuid.uuid4()
    passage = _passage(chunk_id, "iPhone net sales were 209596 million dollars in 2025.")
    answer = GroundedAnswer(
        answer="iPhone net sales were $209.6 billion [1].",
        citations=[
            Citation(
                citation_index=1,
                chunk_id=chunk_id,
                excerpt="iPhone net sales were $209.6 billion.",
            )
        ],
    )

    normalized = normalize_grounded_answer(answer, {chunk_id: passage})
    validate_grounded_answer(normalized, {chunk_id: passage})
    assert "209596" in normalized.citations[0].excerpt


def test_validate_accepts_stock_price_refusal_wording() -> None:
    answer = GroundedAnswer(
        answer=(
            "The SEC filings reviewed do not contain any information regarding "
            "Apple's official stock price target for 2030."
        ),
        citations=[],
    )

    validate_grounded_answer(answer, {})
