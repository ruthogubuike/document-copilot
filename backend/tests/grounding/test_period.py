from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.assistant.outputs import Citation, GroundedAnswer
from app.grounding.period import (
    extract_requested_fiscal_year,
    validate_period_alignment,
)
from app.grounding.validator import GroundingError
from app.retrieval.types import RetrievedPassage


def _passage(*, chunk_id: uuid.UUID, fiscal_year: int) -> RetrievedPassage:
    return RetrievedPassage(
        chunk_id=chunk_id,
        chunk_index=0,
        text="iPhone net sales were $200.6 billion.",
        document_id=uuid.uuid4(),
        ticker="AAPL",
        form="10-K",
        fiscal_year=fiscal_year,
        filing_date=date(fiscal_year, 10, 31),
        accession_number="0000320193-23-000106",
        source_url="https://example.com",
    )


def test_extract_requested_fiscal_year_single_year() -> None:
    assert (
        extract_requested_fiscal_year(
            "What did Apple's 2027 10-K disclose about iPhone revenue?"
        )
        == 2027
    )


def test_extract_requested_fiscal_year_multiple_years_returns_none() -> None:
    assert (
        extract_requested_fiscal_year("Compare Apple 2023 and 2024 iPhone revenue")
        is None
    )


def test_validate_rejects_cited_answer_from_wrong_fiscal_year() -> None:
    chunk_id = uuid.uuid4()
    answer = GroundedAnswer(
        answer="iPhone net sales were $200.6 billion [1].",
        citations=[
            Citation(
                citation_index=1,
                chunk_id=chunk_id,
                excerpt="iPhone net sales were $200.6 billion.",
            )
        ],
    )

    with pytest.raises(GroundingError, match="question asked about 2027"):
        validate_period_alignment(
            "What did Apple's 2027 10-K disclose about iPhone revenue?",
            answer,
            {chunk_id: _passage(chunk_id=chunk_id, fiscal_year=2023)},
        )


def test_validate_rejects_uncited_answer_about_different_filing_year() -> None:
    answer = GroundedAnswer(
        answer=(
            "Apple's 2023 10-K disclosed that iPhone net sales were $200.6 billion, "
            "while Services net sales were $85.2 billion."
        ),
        citations=[],
    )

    with pytest.raises(GroundingError, match="different fiscal year than 2027"):
        validate_period_alignment(
            "What did Apple's 2027 10-K disclose about iPhone revenue?",
            answer,
            {},
        )


def test_validate_accepts_insufficient_evidence_refusal() -> None:
    answer = GroundedAnswer(
        answer=(
            "The corpus does not contain Apple's 2027 10-K. No filing for that "
            "fiscal year is available."
        ),
        citations=[],
    )

    validate_period_alignment(
        "What did Apple's 2027 10-K disclose about iPhone revenue?",
        answer,
        {},
    )
