from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tiktoken
from docling.chunking import HybridChunker
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.hierarchical_chunker import (
    ChunkingDocSerializer,
    ChunkingSerializerProvider,
    DocChunk,
)
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer
from docling_core.transforms.serializer.markdown import MarkdownTableSerializer

from app.config import settings
from app.database.models.constants import EMBEDDING_DIMENSIONS

# OpenAI embedding input limit for text-embedding-3-small.
OPENAI_EMBEDDING_MAX_INPUT_TOKENS = 8191
# HybridChunker contextualize() can add heading prefixes — stay below the embed limit.
CHUNKER_MAX_TOKENS = 7680
EMBED_BATCH_SIZE = 128

_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_SEPARATOR_CELL_RE = re.compile(r"^:?-+:?$")


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return any("-" in cell for cell in cells) and all(
        cell == "" or _SEPARATOR_CELL_RE.match(cell) for cell in cells
    )


def _clean_table_block(block: list[str]) -> list[str]:
    """Collapse docling's mangled financial tables.

    SEC filing tables come back with the row-label column repeated several times
    and numeric cells scattered across empty spacer columns. Drop columns that are
    empty in every data row and columns that exactly duplicate the previous kept
    column, then rebuild the grid.
    """
    rows = [_split_table_row(line) for line in block]
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    separator_flags = [_is_separator_row(row) for row in rows]
    data_indexes = [i for i, is_sep in enumerate(separator_flags) if not is_sep]
    if not data_indexes:
        return block

    def column_values(col: int) -> list[str]:
        return [rows[i][col] for i in data_indexes]

    kept_columns: list[int] = []
    for col in range(width):
        values = column_values(col)
        if all(value == "" for value in values):
            continue
        if kept_columns and values == column_values(kept_columns[-1]):
            continue
        kept_columns.append(col)

    if not kept_columns:
        return block

    cleaned: list[str] = []
    for i, row in enumerate(rows):
        if separator_flags[i]:
            cleaned.append("| " + " | ".join("---" for _ in kept_columns) + " |")
            continue
        cells = [row[col] for col in kept_columns]
        if all(cell == "" for cell in cells):
            continue
        cleaned.append("| " + " | ".join(cells) + " |")
    return cleaned


def clean_markdown_tables(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        if not _TABLE_ROW_RE.match(lines[i]):
            out.append(lines[i])
            i += 1
            continue
        j = i
        while j < len(lines) and _TABLE_ROW_RE.match(lines[j]):
            j += 1
        block = lines[i:j]
        has_separator = any(
            _is_separator_row(_split_table_row(line)) for line in block
        )
        out.extend(_clean_table_block(block) if has_separator else block)
        i = j
    return "\n".join(out)


class PatchedOpenAITokenizer(OpenAITokenizer):
    """Allow SEC filing text that contains tiktoken special-token strings."""

    def count_tokens(self, text: str) -> int:
        return len(
            self.tokenizer.encode(
                text,
                allowed_special="all",
                disallowed_special=(),
            )
        )


class MDTableSerializerProvider(ChunkingSerializerProvider):
    def get_serializer(self, doc: Any) -> ChunkingDocSerializer:
        return ChunkingDocSerializer(
            doc=doc,
            table_serializer=MarkdownTableSerializer(),
        )


@dataclass(frozen=True)
class ChunkRecord:
    chunk_index: int
    text: str
    token_count: int
    page: str | None
    section: str | None
    chunk_metadata: dict[str, Any]


def build_hybrid_chunker() -> HybridChunker:
    tokenizer = PatchedOpenAITokenizer(
        tokenizer=tiktoken.encoding_for_model(settings.openai_embedding_model),
        max_tokens=CHUNKER_MAX_TOKENS,
    )
    return HybridChunker(
        tokenizer=tokenizer,
        merge_peers=True,
        repeat_table_header=True,
        serializer_provider=MDTableSerializerProvider(),
    )


def convert_html_to_document(html_path: Path) -> Any:
    return DocumentConverter().convert(str(html_path)).document


def page_from_chunk(chunk: DocChunk) -> str | None:
    for item in chunk.meta.doc_items:
        if not item.prov:
            continue
        for prov in item.prov:
            if prov.page_no is not None:
                return str(prov.page_no)
    return None


def section_from_chunk(chunk: DocChunk) -> str | None:
    if not chunk.meta.headings:
        return None
    return " > ".join(chunk.meta.headings)


def chunk_metadata_from_doc_chunk(
    chunk: DocChunk,
    *,
    filing: dict[str, Any],
    raw_text: str,
) -> dict[str, Any]:
    return {
        "ticker": filing["ticker"],
        "cik": filing["cik"],
        "form": filing["form"],
        "filing_date": filing["filing_date"],
        "report_date": filing.get("report_date"),
        "fiscal_year": filing.get("fiscal_year"),
        "accession_number": filing["accession_number"],
        "headings": chunk.meta.headings,
        "doc_item_labels": [str(item.label) for item in chunk.meta.doc_items],
        "doc_item_refs": [item.self_ref for item in chunk.meta.doc_items],
        "chunker": "hybrid",
        "raw_text": raw_text,
    }


def chunk_record_from_doc_chunk(
    chunk: DocChunk,
    *,
    chunk_index: int,
    chunker: HybridChunker,
    tokenizer: PatchedOpenAITokenizer,
    filing: dict[str, Any],
) -> ChunkRecord:
    raw_text = clean_markdown_tables(chunk.text)
    text = clean_markdown_tables(chunker.contextualize(chunk=chunk))
    token_count = tokenizer.count_tokens(text)
    if token_count > OPENAI_EMBEDDING_MAX_INPUT_TOKENS:
        text = raw_text
        token_count = tokenizer.count_tokens(text)
    if token_count > OPENAI_EMBEDDING_MAX_INPUT_TOKENS:
        encoded = tokenizer.tokenizer.encode(
            text,
            allowed_special="all",
            disallowed_special=(),
        )[:OPENAI_EMBEDDING_MAX_INPUT_TOKENS]
        text = tokenizer.tokenizer.decode(encoded)
        token_count = len(encoded)

    return ChunkRecord(
        chunk_index=chunk_index,
        text=text,
        token_count=token_count,
        page=page_from_chunk(chunk),
        section=section_from_chunk(chunk),
        chunk_metadata=chunk_metadata_from_doc_chunk(
            chunk,
            filing=filing,
            raw_text=raw_text,
        ),
    )


def chunk_html_filing(
    html_path: Path,
    filing: dict[str, Any],
) -> list[ChunkRecord]:
    chunker = build_hybrid_chunker()
    tokenizer = chunker.tokenizer
    document = convert_html_to_document(html_path)
    records: list[ChunkRecord] = []

    for chunk_index, chunk in enumerate(chunker.chunk(dl_doc=document)):
        doc_chunk = DocChunk.model_validate(chunk)
        if not doc_chunk.text.strip() and not doc_chunk.meta.headings:
            continue
        records.append(
            chunk_record_from_doc_chunk(
                doc_chunk,
                chunk_index=len(records),
                chunker=chunker,
                tokenizer=tokenizer,
                filing=filing,
            )
        )

    return records


def assert_embedding_dimensions(embedding: list[float]) -> list[float]:
    if len(embedding) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Expected embedding dimension {EMBEDDING_DIMENSIONS}, got {len(embedding)}"
        )
    return embedding
