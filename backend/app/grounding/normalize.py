from __future__ import annotations

import uuid

from app.assistant.outputs import MAX_CITATION_EXCERPT, Citation, GroundedAnswer
from app.grounding.repair import repair_grounded_answer
from app.grounding.validator import _excerpt_in_chunk, _normalize_whitespace
from app.retrieval.types import RetrievedPassage


def _fallback_excerpt(chunk_text: str) -> str:
    return _normalize_whitespace(chunk_text)[:MAX_CITATION_EXCERPT]


def _resolved_excerpt(requested: str, chunk_text: str) -> str:
    if _excerpt_in_chunk(requested, chunk_text):
        return _normalize_whitespace(requested)[:MAX_CITATION_EXCERPT]
    return _fallback_excerpt(chunk_text)


def normalize_grounded_answer(
    answer: GroundedAnswer,
    retrieved_chunks: dict[uuid.UUID, RetrievedPassage],
) -> GroundedAnswer:
    answer = repair_grounded_answer(answer, retrieved_chunks)
    fixed_citations: list[Citation] = []
    for citation in answer.citations:
        passage = retrieved_chunks.get(citation.chunk_id)
        if passage is None:
            fixed_citations.append(citation)
            continue
        fixed_citations.append(
            citation.model_copy(
                update={
                    "excerpt": _resolved_excerpt(citation.excerpt, passage.text),
                }
            )
        )
    return answer.model_copy(update={"citations": fixed_citations})
