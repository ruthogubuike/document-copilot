from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

COMPANY_NAMES: dict[str, str] = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
}


@dataclass(frozen=True)
class FilingManifestEntry:
    ticker: str
    cik: str
    form: str
    filing_date: date
    report_date: date | None
    fiscal_year: int
    accession_number: str
    primary_document: str
    source_url: str
    local_path: Path
    markdown_content: str
    company_name: str | None


def load_manifest(manifest_path: Path) -> list[dict]:
    return json.loads(manifest_path.read_text(encoding="utf-8"))["filings"]


def resolve_markdown_path(markdown_dir: Path, local_path: str) -> Path:
    return markdown_dir / Path(local_path.replace("\\", "/"))


def resolve_html_path(downloads_dir: Path, local_path: str) -> Path:
    return downloads_dir / Path(local_path.replace("\\", "/"))


def filings_by_accession(manifest_path: Path) -> dict[str, dict]:
    return {entry["accession_number"]: entry for entry in load_manifest(manifest_path)}


def filing_from_manifest_entry(
    entry: dict,
    *,
    markdown_dir: Path,
) -> FilingManifestEntry:
    markdown_path = resolve_markdown_path(markdown_dir, entry["local_path"])
    report_date = (
        date.fromisoformat(entry["report_date"]) if entry.get("report_date") else None
    )
    filing_date = date.fromisoformat(entry["filing_date"])
    fiscal_year = report_date.year if report_date else filing_date.year
    ticker = entry["ticker"]

    return FilingManifestEntry(
        ticker=ticker,
        cik=entry["cik"],
        form=entry["form"],
        filing_date=filing_date,
        report_date=report_date,
        fiscal_year=fiscal_year,
        accession_number=entry["accession_number"],
        primary_document=entry["primary_document"],
        source_url=entry["source_url"],
        local_path=markdown_path,
        markdown_content=markdown_path.read_text(encoding="utf-8"),
        company_name=COMPANY_NAMES.get(ticker),
    )
