from __future__ import annotations

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.documents import get_source_document_by_accession, insert_chunks
from app.database.models import DocumentChunk
from app.database.models.constants import EMBEDDING_DIMENSIONS
from ingest.chunking import chunk_html_filing
from ingest.embeddings import embed_texts
from ingest.load_chunks import (
    DOWNLOADS_DIR,
    DOWNLOADS_MANIFEST,
    chunk_records_to_rows,
    filing_context_from_document,
    html_path_for_document,
)

# Params: edit these, then run `uv run python -m ingest.smoke_test_chunk`
SMOKE_ACCESSION = "0000320193-25-000079"
SMOKE_CHUNK_INDEX = 999_999
DELETE_AFTER_VERIFY = True


def verify_chunk_row(session: Session, chunk_id) -> None:
    row = session.scalar(select(DocumentChunk).where(DocumentChunk.id == chunk_id))
    if row is None:
        raise RuntimeError("Inserted chunk row not found")

    if row.embedding is None:
        raise RuntimeError("Chunk embedding is null")

    if len(row.embedding) != EMBEDDING_DIMENSIONS:
        raise RuntimeError(
            f"Unexpected embedding size: {len(row.embedding)} "
            f"(expected {EMBEDDING_DIMENSIONS})"
        )

    if not row.text.strip():
        raise RuntimeError("Chunk text is empty")

    print(f"Verified chunk {row.id}")
    print(f"  document_id: {row.document_id}")
    print(f"  chunk_index: {row.chunk_index}")
    print(f"  token_count: {row.token_count}")
    print(f"  section: {row.section!r}")
    print(f"  text preview: {row.text[:200]!r}...")


def run_smoke_test() -> None:
    if not DOWNLOADS_MANIFEST.exists():
        raise SystemExit(
            f"Missing {DOWNLOADS_MANIFEST}. Run `uv run data/download.py` first."
        )

    engine = create_engine(settings.sqlalchemy_database_url)

    with Session(engine) as session:
        document = get_source_document_by_accession(session, SMOKE_ACCESSION)
        if document is None:
            raise SystemExit(
                f"Source document {SMOKE_ACCESSION} not found. "
                "Run `uv run python -m ingest.load_source_documents` first."
            )

        html_path = html_path_for_document(
            document,
            downloads_dir=DOWNLOADS_DIR,
            manifest_path=DOWNLOADS_MANIFEST,
        )
        filing = filing_context_from_document(document)

        session.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document.id,
                DocumentChunk.chunk_index == SMOKE_CHUNK_INDEX,
            )
        )

        records = chunk_html_filing(html_path, filing)
        if not records:
            raise RuntimeError("Chunker returned no chunks for smoke-test filing")

        first = records[0]
        print(
            f"Smoke chunk 0: {first.token_count} tokens, "
            f"section={first.section!r}"
        )
        embeddings = embed_texts([first.text])
        rows = chunk_records_to_rows([first], embeddings)
        rows[0]["chunk_index"] = SMOKE_CHUNK_INDEX
        rows[0]["chunk_metadata"] = {
            **rows[0]["chunk_metadata"],
            "smoke_test": True,
        }

        insert_chunks(session, document_id=document.id, chunk_rows=rows)
        session.flush()

        inserted = session.scalar(
            select(DocumentChunk).where(
                DocumentChunk.document_id == document.id,
                DocumentChunk.chunk_index == SMOKE_CHUNK_INDEX,
            )
        )
        if inserted is None:
            raise RuntimeError("Failed to load inserted smoke-test chunk")

        verify_chunk_row(session, inserted.id)

        if DELETE_AFTER_VERIFY:
            session.execute(delete(DocumentChunk).where(DocumentChunk.id == inserted.id))
            session.commit()
            print("Deleted smoke-test chunk after verification.")
        else:
            session.commit()
            print("Kept smoke-test chunk in the database.")


if __name__ == "__main__":
    run_smoke_test()
