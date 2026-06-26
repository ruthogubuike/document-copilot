"""Unit tests for AI SDK message conversion."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from app.chat.messages import (
    UIMessage,
    UIMessagePart,
    citation_parts,
    derive_thread_title,
    extract_text_from_parts,
    latest_user_message,
    message_row_to_ui,
    messages_to_agent_history,
    ui_message_to_persist,
)
from app.database.chats import ChatMessageRow


def test_derive_thread_title_keeps_short_question() -> None:
    assert (
        derive_thread_title("What was Apple's fiscal 2024 revenue?")
        == "What was Apple's fiscal 2024 revenue?"
    )


def test_derive_thread_title_collapses_whitespace_and_capitalizes() -> None:
    assert derive_thread_title("  compare\n  aws   margins ") == "Compare aws margins"


def test_derive_thread_title_truncates_long_text_on_word_boundary() -> None:
    text = (
        "Compare AWS operating income and margin against North America "
        "for Amazon across recent years"
    )
    title = derive_thread_title(text)
    assert title.endswith("…")
    assert len(title) <= 61
    assert "  " not in title


def test_derive_thread_title_falls_back_for_blank_text() -> None:
    assert derive_thread_title("   ") == "New chat"


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


def test_messages_to_agent_history_excludes_latest_user_turn() -> None:
    messages = [
        UIMessage(id="1", role="user", parts=[UIMessagePart(type="text", text="First")]),
        UIMessage(
            id="2",
            role="assistant",
            parts=[UIMessagePart(type="text", text="Reply")],
        ),
        UIMessage(
            id="3",
            role="user",
            parts=[UIMessagePart(type="text", text="Follow up")],
        ),
    ]

    history = messages_to_agent_history(messages)

    assert len(history) == 2
    assert history[0].parts[0].content == "First"
    assert history[1].parts[0].content == "Reply"


def test_citation_parts_include_filing_metadata() -> None:
    import uuid
    from datetime import date

    from app.assistant.outputs import Citation
    from app.retrieval.types import RetrievedPassage

    document_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    neighbor_before_id = uuid.uuid4()
    neighbor_after_id = uuid.uuid4()

    def _chunk(chunk_uuid: uuid.UUID, chunk_index: int, text: str) -> RetrievedPassage:
        return RetrievedPassage(
            chunk_id=chunk_uuid,
            chunk_index=chunk_index,
            text=text,
            document_id=document_id,
            ticker="AAPL",
            company_name="Apple Inc.",
            form="10-K",
            fiscal_year=2025,
            filing_date=date(2025, 10, 31),
            accession_number="0000320193-25-000079",
            source_url="https://example.com",
        )

    passage = _chunk(chunk_id, 1, "Revenue mix shifted toward Services.")
    passage = passage.model_copy(
        update={
            "neighbor_chunks": [
                _chunk(neighbor_after_id, 2, "Services grew year over year."),
                _chunk(neighbor_before_id, 0, "Net sales increased in fiscal 2025."),
            ]
        }
    )
    parts = citation_parts(
        [
            Citation(
                citation_index=1,
                chunk_id=chunk_id,
                excerpt="Revenue mix shifted toward Services.",
            )
        ],
        {chunk_id: passage},
    )

    assert parts[0]["type"] == "data-citation"
    assert parts[0]["data"]["ticker"] == "AAPL"
    assert parts[0]["data"]["companyName"] == "Apple Inc."
    assert parts[0]["data"]["chunkIndex"] == 1

    context = parts[0]["data"]["context"]
    assert [chunk["chunkIndex"] for chunk in context] == [0, 1, 2]
    assert [chunk["isCited"] for chunk in context] == [False, True, False]
    assert context[1]["text"] == "Revenue mix shifted toward Services."
