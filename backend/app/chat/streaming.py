"""AI SDK v5 UI message stream (SSE) emission."""

from __future__ import annotations

import asyncio
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


async def stream_stub_reply(text: str) -> AsyncIterator[str]:
    message_id = f"msg_{uuid.uuid4().hex}"
    text_id = f"text_{uuid.uuid4().hex}"

    yield _sse_event({"type": "start", "messageId": message_id})
    yield _sse_event({"type": "text-start", "id": text_id})

    words = text.split(" ")
    for index, word in enumerate(words):
        delta = word if index == 0 else f" {word}"
        yield _sse_event({"type": "text-delta", "id": text_id, "delta": delta})
        await asyncio.sleep(0.02)

    yield _sse_event({"type": "text-end", "id": text_id})
    yield _sse_event({"type": "finish"})
    yield "data: [DONE]\n\n"
