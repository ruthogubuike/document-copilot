"""Detect when an answer uses filings from the wrong fiscal period."""

from __future__ import annotations

import re
import uuid

from app.assistant.outputs import GroundedAnswer
from app.grounding.validator import GroundingError, _has_insufficient_evidence_wording
from app.retrieval.types import RetrievedPassage

_YEAR_RE = re.compile(r"\b(20\d{2})\b")


def extract_requested_fiscal_year(user_query: str) -> int | None:
    """Return a single fiscal year when the question targets one period."""
    years = sorted({int(match) for match in _YEAR_RE.findall(user_query)})
    if len(years) == 1:
        return years[0]
    return None


def _answer_presents_different_filing_year(answer: str, requested: int) -> bool:
    lowered = answer.lower()
    for year_str in _YEAR_RE.findall(answer):
        year = int(year_str)
        if year == requested:
            continue
        patterns = (
            f"{year_str} 10-k",
            f"fiscal year {year_str}",
            f"{year_str} fiscal year",
            f"year {year_str}",
        )
        if any(pattern in lowered for pattern in patterns):
            return True
    return False


def validate_period_alignment(
    user_query: str,
    answer: GroundedAnswer,
    retrieved_chunks: dict[uuid.UUID, RetrievedPassage],
) -> None:
    requested = extract_requested_fiscal_year(user_query)
    if requested is None or _has_insufficient_evidence_wording(answer.answer):
        return

    if answer.citations:
        cited_years = {
            retrieved_chunks[citation.chunk_id].fiscal_year
            for citation in answer.citations
            if citation.chunk_id in retrieved_chunks
        }
        if cited_years and requested not in cited_years:
            years = sorted(cited_years)
            label = str(years[0]) if len(years) == 1 else f"{years[0]}–{years[-1]}"
            raise GroundingError(
                f"Answer cites fiscal year {label} filings but the question asked "
                f"about {requested}. Use only matching filings or state that the "
                "corpus does not contain the requested period."
            )
        return

    if _answer_presents_different_filing_year(answer.answer, requested):
        raise GroundingError(
            f"Answer discusses a different fiscal year than {requested} without "
            "stating insufficient evidence."
        )
