from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import SourceDocument
from ingest.manifest import filing_from_manifest_entry, load_manifest

# Params: edit these, then run `uv run python -m ingest.load_source_documents`
MARKDOWN_DIR = Path(__file__).resolve().parents[2] / "data" / "markdown"
MANIFEST_PATH = MARKDOWN_DIR / "manifest.json"
SKIP_EXISTING = True


def load_source_documents(
    *,
    manifest_path: Path = MANIFEST_PATH,
    markdown_dir: Path = MARKDOWN_DIR,
    skip_existing: bool = SKIP_EXISTING,
) -> tuple[int, int]:
    if not manifest_path.exists():
        raise SystemExit(
            f"Missing {manifest_path}. Run `uv run data/convert_to_markdown.py` first."
        )

    engine = create_engine(settings.sqlalchemy_database_url)
    ingested_at = datetime.now(UTC)
    inserted = 0
    skipped = 0

    with Session(engine) as session:
        for entry in load_manifest(manifest_path):
            filing = filing_from_manifest_entry(entry, markdown_dir=markdown_dir)

            existing = session.scalar(
                select(SourceDocument).where(
                    SourceDocument.accession_number == filing.accession_number
                )
            )
            if existing is not None:
                if skip_existing:
                    print(f"Skipping {filing.accession_number} (already ingested)")
                    skipped += 1
                    continue

                existing.ticker = filing.ticker
                existing.cik = filing.cik
                existing.company_name = filing.company_name
                existing.form = filing.form
                existing.filing_date = filing.filing_date
                existing.report_date = filing.report_date
                existing.fiscal_year = filing.fiscal_year
                existing.primary_document = filing.primary_document
                existing.source_url = filing.source_url
                existing.markdown_content = filing.markdown_content
                existing.ingested_at = ingested_at
                inserted += 1
                continue

            print(
                f"Ingesting {filing.ticker} {filing.fiscal_year} "
                f"({filing.accession_number})..."
            )
            session.add(
                SourceDocument(
                    ticker=filing.ticker,
                    cik=filing.cik,
                    company_name=filing.company_name,
                    form=filing.form,
                    filing_date=filing.filing_date,
                    report_date=filing.report_date,
                    fiscal_year=filing.fiscal_year,
                    accession_number=filing.accession_number,
                    primary_document=filing.primary_document,
                    source_url=filing.source_url,
                    markdown_content=filing.markdown_content,
                    ingested_at=ingested_at,
                )
            )
            inserted += 1

        session.commit()

    return inserted, skipped


if __name__ == "__main__":
    inserted, skipped = load_source_documents()
    print(f"Ingested {inserted} source document(s), skipped {skipped}")
