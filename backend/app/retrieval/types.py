from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field


class RetrievalFilters(BaseModel):
    ticker: str | None = None
    fiscal_year_min: int | None = None
    fiscal_year_max: int | None = None
    form: str = "10-K"


class RankedChunkHit(BaseModel):
    chunk_id: uuid.UUID
    rrf_score: float
    semantic_rank: int | None = None
    fulltext_rank: int | None = None


class RetrievedPassage(BaseModel):
    chunk_id: uuid.UUID
    chunk_index: int
    text: str
    page: str | None = None
    section: str | None = None
    document_id: uuid.UUID
    ticker: str
    company_name: str | None = None
    form: str
    fiscal_year: int | None = None
    filing_date: date
    accession_number: str
    source_url: str
    neighbor_chunks: list[RetrievedPassage] = Field(default_factory=list)
