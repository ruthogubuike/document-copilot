# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "docling==2.102.0",
# ]
# ///
from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from docling.document_converter import DocumentConverter


# Params: edit these, then run `uv run data/convert_to_markdown.py`
INPUT_DIR = Path(__file__).resolve().parent / "downloads"
OUTPUT_DIR = Path(__file__).resolve().parent / "markdown"
CLEAR_OUTPUT_DIR = True


def markdown_path_for(source_relative: str) -> Path:
    relative = Path(source_relative.replace("\\", "/"))
    return relative.with_suffix(".md")


def convert_filings() -> dict:
    manifest_path = INPUT_DIR / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(
            f"Missing {manifest_path}. Run `uv run data/download.py` first."
        )

    source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if CLEAR_OUTPUT_DIR and OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    converter = DocumentConverter()
    manifest = {
        "source": source_manifest["source"],
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "form": source_manifest["form"],
        "converted_count": 0,
        "filings": [],
    }

    for filing in source_manifest["filings"]:
        source_relative = filing["local_path"]
        source_path = INPUT_DIR / Path(source_relative.replace("\\", "/"))
        if not source_path.exists():
            raise SystemExit(f"Missing source file: {source_path}")

        markdown_relative = markdown_path_for(source_relative)
        output_path = OUTPUT_DIR / markdown_relative
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Converting {source_relative}...", flush=True)
        result = converter.convert(str(source_path))
        output_path.write_text(
            result.document.export_to_markdown(),
            encoding="utf-8",
        )

        entry = dict(filing)
        entry["local_path"] = str(output_path.relative_to(OUTPUT_DIR))
        manifest["filings"].append(entry)
        manifest["converted_count"] += 1

    output_manifest_path = OUTPUT_DIR / "manifest.json"
    output_manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    result = convert_filings()
    print(f"Converted {result['converted_count']} filing(s) to {OUTPUT_DIR}")
    print(f"Manifest: {OUTPUT_DIR / 'manifest.json'}")
