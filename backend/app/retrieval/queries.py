from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import DocumentChunk, SourceDocument
from app.retrieval.types import RetrievedPassage, RetrievalFilters


def apply_retrieval_filters(
    stmt: Select,
    filters: RetrievalFilters,
) -> Select:
    stmt = stmt.where(SourceDocument.form == filters.form)
    if filters.ticker is not None:
        stmt = stmt.where(SourceDocument.ticker == filters.ticker)
    if filters.fiscal_year_min is not None:
        stmt = stmt.where(SourceDocument.fiscal_year >= filters.fiscal_year_min)
    if filters.fiscal_year_max is not None:
        stmt = stmt.where(SourceDocument.fiscal_year <= filters.fiscal_year_max)
    return stmt


def _base_passage_select() -> Select:
    return (
        select(DocumentChunk, SourceDocument)
        .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
    )


def passage_from_row(chunk: DocumentChunk, document: SourceDocument) -> RetrievedPassage:
    return RetrievedPassage(
        chunk_id=chunk.id,
        chunk_index=chunk.chunk_index,
        text=chunk.text,
        page=chunk.page,
        section=chunk.section,
        document_id=document.id,
        ticker=document.ticker,
        company_name=document.company_name,
        form=document.form,
        fiscal_year=document.fiscal_year,
        filing_date=document.filing_date,
        accession_number=document.accession_number,
        source_url=document.source_url,
    )


async def semantic_search_ids(
    session: AsyncSession,
    query_embedding: list[float],
    *,
    filters: RetrievalFilters,
    limit: int,
) -> list[uuid.UUID]:
    stmt = _base_passage_select().where(DocumentChunk.embedding.is_not(None))
    stmt = apply_retrieval_filters(stmt, filters)
    stmt = (
        stmt.order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [chunk.id for chunk, _document in rows]


async def fulltext_search_ids(
    session: AsyncSession,
    query: str,
    *,
    filters: RetrievalFilters,
    limit: int,
) -> list[uuid.UUID]:
    tsquery = func.plainto_tsquery("english", query)
    stmt = _base_passage_select().where(DocumentChunk.search_vector.op("@@")(tsquery))
    stmt = apply_retrieval_filters(stmt, filters)
    stmt = stmt.order_by(func.ts_rank(DocumentChunk.search_vector, tsquery).desc()).limit(
        limit
    )
    rows = (await session.execute(stmt)).all()
    return [chunk.id for chunk, _document in rows]


async def fetch_passages_by_ids(
    session: AsyncSession,
    chunk_ids: list[uuid.UUID],
) -> dict[uuid.UUID, RetrievedPassage]:
    if not chunk_ids:
        return {}

    stmt = _base_passage_select().where(DocumentChunk.id.in_(chunk_ids))
    rows = (await session.execute(stmt)).all()
    return {
        chunk.id: passage_from_row(chunk, document) for chunk, document in rows
    }


async def fetch_passage_by_id(
    session: AsyncSession,
    chunk_id: uuid.UUID,
) -> RetrievedPassage | None:
    passages = await fetch_passages_by_ids(session, [chunk_id])
    return passages.get(chunk_id)


async def fetch_neighbor_passages(
    session: AsyncSession,
    *,
    document_id: uuid.UUID,
    chunk_index: int,
    window: int,
    exclude_chunk_id: uuid.UUID | None = None,
) -> list[RetrievedPassage]:
    if window < 1:
        return []

    stmt = (
        _base_passage_select()
        .where(DocumentChunk.document_id == document_id)
        .where(DocumentChunk.chunk_index >= chunk_index - window)
        .where(DocumentChunk.chunk_index <= chunk_index + window)
        .order_by(DocumentChunk.chunk_index)
    )
    rows = (await session.execute(stmt)).all()
    passages = [
        passage_from_row(chunk, document)
        for chunk, document in rows
        if exclude_chunk_id is None or chunk.id != exclude_chunk_id
    ]
    return passages
