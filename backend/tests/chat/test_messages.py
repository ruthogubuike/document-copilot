"""Unit tests for AI SDK message conversion."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from app.chat.messages import (
    UIMessage,
    UIMessagePart,
    extract_text_from_parts,
    latest_user_message,
    message_row_to_ui,
    ui_message_to_persist,
)
from app.database.chats import ChatMessageRow


def test_extract_text_from_parts_joins_text_parts() -> None:
    parts = [
        UIMessagePart(type="text", text="Hello "),
        UIMessagePart(type="text", text="world"),
    ]
    assert extract_text_from_parts(parts) == "Hello world"


def test_latest_user_message_returns_last_user_turn() -> None:
    messages = [
        UIMessage(id="1", role="user", parts=[UIMessagePart(type="text", text="Hi")]),
        UIMessage(
            id="2",
            role="assistant",
            parts=[UIMessagePart(type="text", text="Hello")],
        ),
        UIMessage(
            id="3",
            role="user",
            parts=[UIMessagePart(type="text", text="Follow up")],
        ),
    ]
    latest = latest_user_message(messages)
    assert latest.id == "3"
    assert extract_text_from_parts(latest.parts) == "Follow up"


def test_latest_user_message_raises_without_user_message() -> None:
    messages = [
        UIMessage(
            id="1",
            role="assistant",
            parts=[UIMessagePart(type="text", text="Hello")],
        ),
    ]
    with pytest.raises(HTTPException) as exc_info:
        latest_user_message(messages)
    assert exc_info.value.status_code == 422


def test_message_row_to_ui_uses_parts_when_present() -> None:
    row = ChatMessageRow(
        id=uuid.uuid4(),
        thread_id=uuid.uuid4(),
        role="assistant",
        content="fallback",
        parts=[{"type": "text", "text": "from parts"}],
        sequence=1,
        created_at=datetime.now(UTC),
    )
    ui = message_row_to_ui(row)
    assert ui.parts[0].text == "from parts"


def test_ui_message_to_persist_builds_content_and_parts() -> None:
    message = UIMessage(
        id="1",
        role="user",
        parts=[UIMessagePart(type="text", text="Question?")],
    )
    content, parts = ui_message_to_persist(message)
    assert content == "Question?"
    assert parts == [{"type": "text", "text": "Question?"}]
