"""Unit tests for grounded turn orchestration."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.assistant.outputs import Citation, GroundedAnswer
from app.auth.dependencies import AuthenticatedUser
from app.chat.messages import UIMessage, UIMessagePart
from app.chat.orchestrator import run_grounded_turn
from app.database.chats import ChatMessageRow
from app.grounding.validator import GroundingError
from app.retrieval.types import RetrievedPassage

USER_ID = uuid.uuid4()
THREAD_ID = uuid.uuid4()
CHUNK_ID = uuid.uuid4()
NOW = datetime.now(UTC)


def _user() -> AuthenticatedUser:
    return AuthenticatedUser(id=USER_ID, email="user@example.com")


def _messages() -> list[UIMessage]:
    return [
        UIMessage(
            id="1",
            role="user",
            parts=[UIMessagePart(type="text", text="What did Apple disclose?")],
        )
    ]


def _passage() -> RetrievedPassage:
    return RetrievedPassage(
        chunk_id=CHUNK_ID,
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


def _grounded_answer() -> GroundedAnswer:
    return GroundedAnswer(
        answer="iPhone revenue was $201 billion [1].",
        citations=[
            Citation(
                citation_index=1,
                chunk_id=CHUNK_ID,
                excerpt="iPhone revenue was $201 billion.",
            )
        ],
    )


class _FakeStreamResult:
    def __init__(self, output: GroundedAnswer) -> None:
        self._output = output

    async def stream_output(self) -> AsyncIterator[GroundedAnswer]:
        yield self._output

    async def get_output(self) -> GroundedAnswer:
        return self._output


@asynccontextmanager
async def _fake_run_stream(*_args, **_kwargs):
    yield _FakeStreamResult(_grounded_answer())


@asynccontextmanager
async def _fake_session():
    yield AsyncMock()


async def _collect() -> list[str]:
    chunks: list[str] = []
    async for chunk in run_grounded_turn(
        thread_id=THREAD_ID,
        messages=_messages(),
        user=_user(),
        token="token",
    ):
        chunks.append(chunk)
    return chunks


@pytest.mark.asyncio
async def test_run_grounded_turn_streams_and_persists() -> None:
    assistant_row = ChatMessageRow(
        id=uuid.uuid4(),
        thread_id=THREAD_ID,
        role="assistant",
        content="answer",
        parts=[{"type": "text", "text": "answer"}],
        sequence=1,
        created_at=NOW,
    )

    with (
        patch("app.chat.orchestrator.require_thread_access"),
        patch("app.chat.orchestrator.ensure_user"),
        patch("app.chat.orchestrator.get_async_session", _fake_session),
        patch("app.chat.orchestrator.document_agent.run_stream", _fake_run_stream),
        patch("app.chat.orchestrator.validate_grounded_answer"),
        patch("app.chat.orchestrator.normalize_grounded_answer", side_effect=lambda answer, _chunks: answer),
        patch(
            "app.chat.orchestrator.citation_parts",
            return_value=[{"type": "data-citation", "data": {"citationIndex": 1}}],
        ),
        patch("app.chat.orchestrator.create_user_client"),
        patch(
            "app.chat.orchestrator.append_messages",
            return_value=(MagicMock(), assistant_row),
        ) as append_messages,
        patch("app.chat.orchestrator.append_citations") as append_citations,
    ):
        chunks = await _collect()

    body = "".join(chunks)
    assert '"type":"text-delta"' in body.replace(" ", "")
    assert '"type":"data-citation"' in body.replace(" ", "")
    assert '"type":"finish"' in body.replace(" ", "")
    assert "data: [DONE]" in body
    append_messages.assert_called_once()
    append_citations.assert_called_once()


@pytest.mark.asyncio
async def test_run_grounded_turn_does_not_persist_on_grounding_error() -> None:
    bad_answer = GroundedAnswer(
        answer="Unsupported claim [1].",
        citations=[
            Citation(
                citation_index=1,
                chunk_id=uuid.uuid4(),
                excerpt="missing",
            )
        ],
    )

    @asynccontextmanager
    async def bad_run_stream(*_args, **_kwargs):
        yield _FakeStreamResult(bad_answer)

    with (
        patch("app.chat.orchestrator.require_thread_access"),
        patch("app.chat.orchestrator.ensure_user"),
        patch("app.chat.orchestrator.get_async_session", _fake_session),
        patch("app.chat.orchestrator.document_agent.run_stream", bad_run_stream),
        patch("app.chat.orchestrator.append_messages") as append_messages,
        patch("app.chat.orchestrator.append_citations") as append_citations,
    ):
        chunks = await _collect()

    body = "".join(chunks)
    assert '"type":"error"' in body.replace(" ", "")
    append_messages.assert_not_called()
    append_citations.assert_not_called()


@pytest.mark.asyncio
async def test_run_grounded_turn_maps_validator_failure_to_error_event() -> None:
    with (
        patch("app.chat.orchestrator.require_thread_access"),
        patch("app.chat.orchestrator.ensure_user"),
        patch("app.chat.orchestrator.get_async_session", _fake_session),
        patch("app.chat.orchestrator.document_agent.run_stream", _fake_run_stream),
        patch(
            "app.chat.orchestrator.validate_grounded_answer",
            side_effect=GroundingError("bad citations"),
        ),
        patch("app.chat.orchestrator.append_messages") as append_messages,
    ):
        chunks = await _collect()

    payload = json.loads(chunks[-2].removeprefix("data: ").strip())
    assert payload["type"] == "error"
    assert payload["errorText"] == "bad citations"
    append_messages.assert_not_called()
