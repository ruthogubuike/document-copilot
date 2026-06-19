from datetime import date
from pathlib import Path

from ingest.manifest import filing_from_manifest_entry, resolve_markdown_path


def test_resolve_markdown_path_normalizes_windows_separators(tmp_path: Path) -> None:
    path = resolve_markdown_path(tmp_path, "2025\\aapl_10-k.md")
    assert path == tmp_path / "2025" / "aapl_10-k.md"


def test_filing_from_manifest_entry_reads_markdown_and_metadata(tmp_path: Path) -> None:
    markdown_dir = tmp_path / "markdown"
    year_dir = markdown_dir / "2025"
    year_dir.mkdir(parents=True)
    markdown_path = year_dir / "aapl_10-k_2025-10-31_0000320193-25-000079.md"
    markdown_path.write_text("# Apple 10-K\n", encoding="utf-8")

    filing = filing_from_manifest_entry(
        {
            "ticker": "AAPL",
            "cik": "0000320193",
            "form": "10-K",
            "filing_date": "2025-10-31",
            "report_date": "2025-09-27",
            "accession_number": "0000320193-25-000079",
            "primary_document": "aapl-20250927.htm",
            "source_url": "https://example.com/aapl.htm",
            "local_path": "2025\\aapl_10-k_2025-10-31_0000320193-25-000079.md",
        },
        markdown_dir=markdown_dir,
    )

    assert filing.ticker == "AAPL"
    assert filing.filing_date == date(2025, 10, 31)
    assert filing.report_date == date(2025, 9, 27)
    assert filing.fiscal_year == 2025
    assert filing.company_name == "Apple Inc."
    assert filing.markdown_content == "# Apple 10-K\n"
    assert filing.local_path == markdown_path
