from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database.models import DocumentChunk, SourceDocument


def get_source_document_by_accession(
    session: Session,
    accession_number: str,
) -> SourceDocument | None:
    return session.scalar(
        select(SourceDocument).where(
            SourceDocument.accession_number == accession_number
        )
    )


def document_has_chunks(session: Session, document_id: uuid.UUID) -> bool:
    count = session.scalar(
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
    )
    return bool(count)


def delete_chunks_for_document(session: Session, document_id: uuid.UUID) -> int:
    result = session.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
    )
    return result.rowcount or 0


def insert_chunks(
    session: Session,
    *,
    document_id: uuid.UUID,
    chunk_rows: list[dict[str, Any]],
) -> int:
    for row in chunk_rows:
        session.add(
            DocumentChunk(
                document_id=document_id,
                chunk_index=row["chunk_index"],
                page=row.get("page"),
                section=row.get("section"),
                text=row["text"],
                token_count=row.get("token_count"),
                embedding=row.get("embedding"),
                chunk_metadata=row.get("chunk_metadata", {}),
            )
        )
    return len(chunk_rows)
