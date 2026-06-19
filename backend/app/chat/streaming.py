"""AI SDK v5 UI message stream (SSE) emission."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

UI_MESSAGE_STREAM_HEADER = "x-vercel-ai-ui-message-stream"
UI_MESSAGE_STREAM_VERSION = "v1"

STREAM_HEADERS = {
    UI_MESSAGE_STREAM_HEADER: UI_MESSAGE_STREAM_VERSION,
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
}


def _sse_event(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"


def sse_start(message_id: str | None = None) -> str:
    return _sse_event(
        {"type": "start", "messageId": message_id or f"msg_{uuid.uuid4().hex}"}
    )


def sse_text_start(text_id: str | None = None) -> tuple[str, str]:
    resolved = text_id or f"text_{uuid.uuid4().hex}"
    return resolved, _sse_event({"type": "text-start", "id": resolved})


def sse_text_delta(text_id: str, delta: str) -> str:
    return _sse_event({"type": "text-delta", "id": text_id, "delta": delta})


def sse_text_end(text_id: str) -> str:
    return _sse_event({"type": "text-end", "id": text_id})


def sse_citation_part(part: dict[str, Any]) -> str:
    return _sse_event(part)


def sse_finish() -> str:
    return _sse_event({"type": "finish"})


def sse_error(error_text: str) -> str:
    return _sse_event({"type": "error", "errorText": error_text})


def sse_done() -> str:
    return "data: [DONE]\n\n"


async def stream_text_deltas(
    text_id: str,
    *,
    deltas: AsyncIterator[str],
) -> AsyncIterator[str]:
    async for delta in deltas:
        if delta:
            yield sse_text_delta(text_id, delta)


async def stream_answer_parts(
    *,
    answer_text: str,
    citation_parts: list[dict[str, Any]],
) -> AsyncIterator[str]:
    message_id = f"msg_{uuid.uuid4().hex}"
    text_id, text_start = sse_text_start()

    yield sse_start(message_id)
    yield text_start
    yield sse_text_delta(text_id, answer_text)
    yield sse_text_end(text_id)

    for part in citation_parts:
        yield sse_citation_part(part)

    yield sse_finish()
    yield sse_done()
