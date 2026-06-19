# Data

Local data artifacts for development live here.

- `downloads/` holds raw source files fetched from SEC EDGAR, grouped by year.
- `markdown/` holds Docling-converted markdown exports with the same year layout and manifest.
- Downloaded and converted payloads are gitignored because the corpus can get large.
- Fetch a sample corpus with `uv run data/download.py`
- Convert downloaded HTML filings to markdown with `uv run data/convert_to_markdown.py`
