from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class Citation(BaseModel):
    citation_index: int = Field(ge=1)
    chunk_id: uuid.UUID
    excerpt: str = Field(max_length=2000)


class GroundedAnswer(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
