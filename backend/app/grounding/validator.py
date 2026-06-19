from __future__ import annotations

import re
import uuid

from app.assistant.outputs import GroundedAnswer
from app.retrieval.types import RetrievedPassage

_CITATION_MARKER_RE = re.compile(r"\[(\d+)\]")

_INSUFFICIENT_EVIDENCE_PHRASES = (
    "not enough evidence",
    "insufficient evidence",
    "corpus does not contain",
    "does not contain enough",
    "does not contain any",
    "do not contain any",
    "do not contain",
    "cannot find",
    "no evidence",
    "not in the corpus",
    "do not support that inference",
    "filings do not",
    "no information",
    "not disclosed",
    "no disclosed",
    "not stated",
    "no stated",
    "not available",
    "filings reviewed",
)


class GroundingError(Exception):
    """Raised when a grounded answer violates the citation contract."""


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _citation_markers(answer: str) -> list[int]:
    return [int(match) for match in _CITATION_MARKER_RE.findall(answer)]


def _has_insufficient_evidence_wording(answer: str) -> bool:
    lowered = answer.lower()
    return any(phrase in lowered for phrase in _INSUFFICIENT_EVIDENCE_PHRASES)


def _excerpt_in_chunk(excerpt: str, chunk_text: str) -> bool:
    excerpt_norm = _normalize_whitespace(excerpt).lower()
    chunk_norm = _normalize_whitespace(chunk_text).lower()
    return excerpt_norm in chunk_norm


def validate_grounded_answer(
    answer: GroundedAnswer,
    retrieved_chunks: dict[uuid.UUID, RetrievedPassage],
) -> None:
    if not answer.citations:
        if not _has_insufficient_evidence_wording(answer.answer):
            raise GroundingError(
                "Answers without citations must explicitly state insufficient evidence."
            )
        if _citation_marker_references(answer.answer):
            raise GroundingError(
                "Citation markers require matching citations in structured output."
            )
        return

    if not answer.answer.strip():
        raise GroundingError("Grounded answers with citations must include answer text.")

    seen_indexes: set[int] = set()
    for citation in answer.citations:
        if citation.citation_index in seen_indexes:
            raise GroundingError(
                f"Duplicate citation_index {citation.citation_index}."
            )
        seen_indexes.add(citation.citation_index)

        passage = retrieved_chunks.get(citation.chunk_id)
        if passage is None:
            raise GroundingError(
                f"Citation {citation.citation_index} references chunk "
                f"{citation.chunk_id} that was not retrieved in this turn."
            )

        if not _excerpt_in_chunk(citation.excerpt, passage.text):
            raise GroundingError(
                f"Citation {citation.citation_index} excerpt is not a substring of "
                "the retrieved chunk text."
            )

    markers = _citation_markers(answer.answer)
    if not markers:
        raise GroundingError(
            "Answers with citations must include [n] markers in the answer text."
        )

    citation_indexes = {citation.citation_index for citation in answer.citations}
    for marker in markers:
        if marker not in citation_indexes:
            raise GroundingError(
                f"Answer references [{marker}] without a matching citation."
            )

    for citation in answer.citations:
        if citation.citation_index not in markers:
            raise GroundingError(
                f"Citation {citation.citation_index} is missing a [n] marker in the answer."
            )


def _citation_marker_references(answer: str) -> bool:
    return bool(_CITATION_MARKER_RE.search(answer))
