from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.assistant.outputs import Citation, GroundedAnswer
from app.grounding.validator import GroundingError, validate_grounded_answer
from app.retrieval.types import RetrievedPassage


def _passage(chunk_id: uuid.UUID, text: str = "Revenue grew 10 percent year over year.") -> RetrievedPassage:
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


def test_validate_accepts_matching_citations() -> None:
    chunk_id = uuid.uuid4()
    passage = _passage(chunk_id, "Revenue GREW 10 percent year over year.")
    answer = GroundedAnswer(
        answer="Revenue grew [1].",
        citations=[
            Citation(
                citation_index=1,
                chunk_id=chunk_id,
                excerpt="revenue grew 10 percent year over year.",
            )
        ],
    )

    validate_grounded_answer(answer, {chunk_id: passage})


def test_validate_rejects_unknown_chunk_id() -> None:
    chunk_id = uuid.uuid4()
    answer = GroundedAnswer(
        answer="Revenue grew [1].",
        citations=[
            Citation(
                citation_index=1,
                chunk_id=chunk_id,
                excerpt="Revenue grew 10 percent year over year.",
            )
        ],
    )

    with pytest.raises(GroundingError, match="not retrieved"):
        validate_grounded_answer(answer, {})


def test_validate_rejects_orphan_marker() -> None:
    chunk_id = uuid.uuid4()
    passage = _passage(chunk_id)
    answer = GroundedAnswer(
        answer="Revenue grew [1] and margins [2].",
        citations=[
            Citation(
                citation_index=1,
                chunk_id=chunk_id,
                excerpt="Revenue grew 10 percent year over year.",
            )
        ],
    )

    with pytest.raises(GroundingError, match="\\[2\\]"):
        validate_grounded_answer(answer, {chunk_id: passage})


def test_validate_rejects_excerpt_not_in_chunk() -> None:
    chunk_id = uuid.uuid4()
    passage = _passage(chunk_id)
    answer = GroundedAnswer(
        answer="Revenue grew [1].",
        citations=[
            Citation(
                citation_index=1,
                chunk_id=chunk_id,
                excerpt="Margins expanded materially.",
            )
        ],
    )

    with pytest.raises(GroundingError, match="substring"):
        validate_grounded_answer(answer, {chunk_id: passage})


def test_validate_rejects_empty_citations_without_evidence_phrase() -> None:
    answer = GroundedAnswer(
        answer="Apple revenue increased across all segments.",
        citations=[],
    )

    with pytest.raises(GroundingError, match="insufficient evidence"):
        validate_grounded_answer(answer, {})


def test_validate_accepts_empty_citations_with_evidence_phrase() -> None:
    answer = GroundedAnswer(
        answer="The corpus does not contain enough evidence to answer that question.",
        citations=[],
    )

    validate_grounded_answer(answer, {})
