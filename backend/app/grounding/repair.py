"""Repair common LLM grounding output mistakes before validation."""

from __future__ import annotations

import re
import uuid

from app.assistant.outputs import MAX_CITATION_EXCERPT, Citation, GroundedAnswer
from app.grounding.validator import _citation_markers
from app.retrieval.types import RetrievedPassage

_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

_PROSE_CITATION_RE = re.compile(
    rf'\n?\s*Citation:\s*"([\s\S]*?)"\s*\[({_UUID})\]\s*$',
    re.IGNORECASE,
)

_BARE_UUID_MARKER_RE = re.compile(
    rf"\[({_UUID})\]\s*$",
    re.IGNORECASE,
)


def _append_marker_if_missing(answer_text: str, index: int) -> str:
    markers = _citation_markers(answer_text)
    if index in markers:
        return answer_text
    return f"{answer_text.rstrip()} [{index}]"


def repair_grounded_answer(
    answer: GroundedAnswer,
    retrieved_chunks: dict[uuid.UUID, RetrievedPassage],
) -> GroundedAnswer:
    """Convert prose 'Citation: \"...\" [chunk-id]' output into structured citations."""
    if answer.citations:
        return answer

    prose_match = _PROSE_CITATION_RE.search(answer.answer)
    if prose_match:
        excerpt, chunk_id_str = prose_match.group(1), prose_match.group(2)
        try:
            chunk_id = uuid.UUID(chunk_id_str)
        except ValueError:
            return answer
        if chunk_id not in retrieved_chunks:
            return answer

        cleaned = answer.answer[: prose_match.start()].strip()
        cleaned = _append_marker_if_missing(cleaned, 1)
        return GroundedAnswer(
            answer=cleaned,
            citations=[
                Citation(
                    citation_index=1,
                    chunk_id=chunk_id,
                    excerpt=excerpt.strip(),
                )
            ],
        )

    bare_match = _BARE_UUID_MARKER_RE.search(answer.answer)
    if bare_match:
        chunk_id_str = bare_match.group(1)
        try:
            chunk_id = uuid.UUID(chunk_id_str)
        except ValueError:
            return answer
        if chunk_id not in retrieved_chunks:
            return answer

        cleaned = answer.answer[: bare_match.start()].strip()
        cleaned = _append_marker_if_missing(cleaned, 1)
        passage = retrieved_chunks[chunk_id]
        return GroundedAnswer(
            answer=cleaned,
            citations=[
                Citation(
                    citation_index=1,
                    chunk_id=chunk_id,
                    excerpt=passage.text[:MAX_CITATION_EXCERPT],
                )
            ],
        )

    return answer
