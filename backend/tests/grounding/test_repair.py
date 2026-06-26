"""Unit tests for grounding answer repair."""

from __future__ import annotations

import uuid
from datetime import date

from app.assistant.outputs import GroundedAnswer
from app.grounding.normalize import normalize_grounded_answer
from app.grounding.repair import repair_grounded_answer
from app.grounding.validator import validate_grounded_answer
from app.retrieval.types import RetrievedPassage

CHUNK_ID = uuid.UUID("b98808e7-a545-44d3-90d2-7bd7be6c1e4d")
CHUNK_TEXT = (
    "The following table shows disaggregated net sales, as well as the portion of "
    "total net sales that was previously deferred, for 2025, 2024 and 2023 "
    "(in millions): iPhone $209,586 Services (1) $109,158 Total net sales $416,161 "
    "(1) Services net sales include amortization of the deferred value of services "
    "bundled in the sales price of certain products."
)


def _passage() -> RetrievedPassage:
    return RetrievedPassage(
        chunk_id=CHUNK_ID,
        chunk_index=0,
        text=CHUNK_TEXT,
        document_id=uuid.uuid4(),
        ticker="AAPL",
        company_name="Apple Inc.",
        form="10-K",
        fiscal_year=2025,
        filing_date=date(2025, 10, 31),
        accession_number="0000320193-25-000079",
        source_url="https://example.com",
    )


def test_repair_prose_citation_with_chunk_uuid() -> None:
    answer = GroundedAnswer(
        answer=(
            "Apple's 2025 10-K disclosed that iPhone net sales were $209.586 billion "
            "in 2025, compared to Services net sales of $109.158 billion.\n\n"
            'Citation: "The following table shows disaggregated net sales... '
            'iPhone $209,586 ... Services (1) $109,158 ..." '
            f"[{CHUNK_ID}]"
        ),
        citations=[],
    )

    repaired = repair_grounded_answer(answer, {CHUNK_ID: _passage()})
    normalized = normalize_grounded_answer(repaired, {CHUNK_ID: _passage()})
    validate_grounded_answer(normalized, {CHUNK_ID: _passage()})

    assert normalized.citations
    assert normalized.citations[0].citation_index == 1
    assert normalized.citations[0].chunk_id == CHUNK_ID
    assert "[1]" in normalized.answer
    assert "Citation:" not in normalized.answer
    assert str(CHUNK_ID) not in normalized.answer
