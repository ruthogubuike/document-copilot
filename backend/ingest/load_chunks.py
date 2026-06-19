from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.documents import (
    delete_chunks_for_document,
    document_has_chunks,
    insert_chunks,
)
from app.database.models import SourceDocument
from ingest.chunking import ChunkRecord, chunk_html_filing
from ingest.embeddings import embed_texts
from ingest.manifest import filings_by_accession, resolve_html_path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DOWNLOADS_DIR = DATA_DIR / "downloads"
DOWNLOADS_MANIFEST = DOWNLOADS_DIR / "manifest.json"
SKIP_EXISTING = True
FORCE_RECHUNK = False


def filing_context_from_document(document: SourceDocument) -> dict:
    return {
        "ticker": document.ticker,
        "cik": document.cik,
        "form": document.form,
        "filing_date": document.filing_date.isoformat(),
        "report_date": (
            document.report_date.isoformat() if document.report_date else None
        ),
        "fiscal_year": document.fiscal_year,
        "accession_number": document.accession_number,
    }


def html_path_for_document(
    document: SourceDocument,
    *,
    downloads_dir: Path,
    manifest_path: Path,
) -> Path:
    entry = filings_by_accession(manifest_path)[document.accession_number]
    return resolve_html_path(downloads_dir, entry["local_path"])


def chunk_records_to_rows(
    records: list[ChunkRecord],
    embeddings: list[list[float]],
) -> list[dict]:
    if len(records) != len(embeddings):
        raise ValueError(
            f"Chunk/embed mismatch: {len(records)} chunks, {len(embeddings)} embeddings"
        )

    rows: list[dict] = []
    for record, embedding in zip(records, embeddings, strict=True):
        row = asdict(record)
        row["embedding"] = embedding
        rows.append(row)
    return rows


def ingest_chunks_for_document(
    session: Session,
    document: SourceDocument,
    *,
    downloads_dir: Path = DOWNLOADS_DIR,
    manifest_path: Path = DOWNLOADS_MANIFEST,
    skip_existing: bool = SKIP_EXISTING,
    force_rechunk: bool = FORCE_RECHUNK,
) -> tuple[int, str]:
    if document_has_chunks(session, document.id):
        if skip_existing and not force_rechunk:
            return 0, "skipped"
        delete_chunks_for_document(session, document.id)

    html_path = html_path_for_document(
        document,
        downloads_dir=downloads_dir,
        manifest_path=manifest_path,
    )
    if not html_path.exists():
        raise FileNotFoundError(f"Missing HTML source file: {html_path}")

    filing = filing_context_from_document(document)
    records = chunk_html_filing(html_path, filing)
    embeddings = embed_texts([record.text for record in records])
    rows = chunk_records_to_rows(records, embeddings)
    insert_chunks(session, document_id=document.id, chunk_rows=rows)
    return len(rows), "ingested"


def load_chunks(
    *,
    accession_number: str | None = None,
    skip_existing: bool = SKIP_EXISTING,
    force_rechunk: bool = FORCE_RECHUNK,
) -> tuple[int, int, int]:
    if not DOWNLOADS_MANIFEST.exists():
        raise SystemExit(
            f"Missing {DOWNLOADS_MANIFEST}. Run `uv run data/download.py` first."
        )

    engine = create_engine(settings.sqlalchemy_database_url)
    ingested_documents = 0
    skipped_documents = 0
    total_chunks = 0

    with Session(engine) as session:
        query = select(SourceDocument).order_by(
            SourceDocument.ticker,
            SourceDocument.fiscal_year,
        )
        if accession_number is not None:
            query = query.where(SourceDocument.accession_number == accession_number)

        documents = session.scalars(query).all()
        if not documents:
            raise SystemExit("No matching source documents found in the database.")

        for document in documents:
            print(
                f"Chunking {document.ticker} {document.fiscal_year} "
                f"({document.accession_number})..."
            )
            count, status = ingest_chunks_for_document(
                session,
                document,
                skip_existing=skip_existing,
                force_rechunk=force_rechunk,
            )
            if status == "skipped":
                print("  skipped (chunks already exist)")
                skipped_documents += 1
                continue

            session.commit()
            print(f"  ingested {count} chunk(s)")
            ingested_documents += 1
            total_chunks += count

    return ingested_documents, skipped_documents, total_chunks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chunk filings and store embeddings.")
    parser.add_argument(
        "--accession",
        help="Ingest a single filing by accession number.",
    )
    parser.add_argument(
        "--force-rechunk",
        action="store_true",
        help="Delete and rebuild chunks for matching documents.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    ingested, skipped, chunks = load_chunks(
        accession_number=args.accession,
        force_rechunk=args.force_rechunk,
        skip_existing=not args.force_rechunk,
    )
    print(
        f"Done: {ingested} document(s) ingested, {skipped} skipped, "
        f"{chunks} total chunk(s) written"
    )
