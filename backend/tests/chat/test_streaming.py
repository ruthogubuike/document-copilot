"""Unit tests for AI SDK streaming output."""

from __future__ import annotations

import asyncio
import json

from app.chat.streaming import STREAM_HEADERS, stream_stub_reply


def test_stream_stub_reply_emits_required_events() -> None:
    async def collect() -> list[str]:
        chunks: list[str] = []
        async for chunk in stream_stub_reply("Hello world"):
            chunks.append(chunk)
        return chunks

    chunks = asyncio.run(collect())
    body = "".join(chunks)
    assert '"type":"start"' in body.replace(" ", "")
    assert '"type":"text-start"' in body.replace(" ", "")
    assert '"type":"text-delta"' in body.replace(" ", "")
    assert '"type":"text-end"' in body.replace(" ", "")
    assert '"type":"finish"' in body.replace(" ", "")
    assert "data: [DONE]" in body


def test_stream_stub_reply_reconstructs_text() -> None:
    text = "Stub response"

    async def collect_deltas() -> list[str]:
        deltas: list[str] = []
        async for chunk in stream_stub_reply(text):
            if '"text-delta"' in chunk:
                payload = json.loads(chunk.removeprefix("data: ").strip())
                deltas.append(payload["delta"])
        return deltas

    deltas = asyncio.run(collect_deltas())
    assert "".join(deltas) == text


def test_stream_headers_include_ui_message_stream_version() -> None:
    assert STREAM_HEADERS["x-vercel-ai-ui-message-stream"] == "v1"
