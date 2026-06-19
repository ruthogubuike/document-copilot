"""Unit tests for AI SDK streaming output."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date

from app.assistant.outputs import Citation
from app.chat.messages import citation_parts
from app.chat.streaming import (
    STREAM_HEADERS,
    stream_answer_parts,
)
from app.retrieval.types import RetrievedPassage


def test_stream_answer_parts_emits_citations_before_finish() -> None:
    chunk_id = uuid.uuid4()
    passage = RetrievedPassage(
        chunk_id=chunk_id,
        chunk_index=0,
        text="iPhone revenue was $201 billion.",
        document_id=uuid.uuid4(),
        ticker="AAPL",
        form="10-K",
        fiscal_year=2025,
        filing_date=date(2025, 10, 31),
        accession_number="0000320193-25-000079",
        source_url="https://example.com",
    )
    citations = [
        Citation(
            citation_index=1,
            chunk_id=chunk_id,
            excerpt="iPhone revenue was $201 billion.",
        )
    ]
    parts = citation_parts(citations, {chunk_id: passage})

    async def collect() -> list[str]:
        chunks: list[str] = []
        async for chunk in stream_answer_parts(
            answer_text="iPhone revenue was $201 billion [1].",
            citation_parts=parts,
        ):
            chunks.append(chunk)
        return chunks

    chunks = asyncio.run(collect())
    body = "".join(chunks)
    normalized = body.replace(" ", "")

    start_index = normalized.index('"type":"start"')
    citation_index = normalized.index('"type":"data-citation"')
    finish_index = normalized.index('"type":"finish"')
    assert start_index < citation_index < finish_index
    assert "data: [DONE]" in body


def test_stream_answer_parts_reconstructs_text() -> None:
    text = "Grounded answer"

    async def collect_deltas() -> list[str]:
        deltas: list[str] = []
        async for chunk in stream_answer_parts(answer_text=text, citation_parts=[]):
            if '"text-delta"' in chunk:
                payload = json.loads(chunk.removeprefix("data: ").strip())
                deltas.append(payload["delta"])
        return deltas

    deltas = asyncio.run(collect_deltas())
    assert "".join(deltas) == text


def test_stream_headers_include_ui_message_stream_version() -> None:
    assert STREAM_HEADERS["x-vercel-ai-ui-message-stream"] == "v1"
