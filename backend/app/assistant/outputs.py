from __future__ import annotations

import uuid

from pydantic import BaseModel, Field, field_validator

MAX_CITATION_EXCERPT = 500


def _truncate_excerpt(text: str) -> str:
    return " ".join(text.split())[:MAX_CITATION_EXCERPT]


class Citation(BaseModel):
    citation_index: int = Field(ge=1)
    chunk_id: uuid.UUID
    excerpt: str = Field(max_length=MAX_CITATION_EXCERPT)

    @field_validator("excerpt", mode="before")
    @classmethod
    def _cap_excerpt_length(cls, value: object) -> object:
        if isinstance(value, str):
            return _truncate_excerpt(value)
        return value


class GroundedAnswer(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
