"""API route tests with mocked persistence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.auth.dependencies import AuthenticatedUser, get_bearer_token, get_current_user
from app.database.chats import ChatMessageRow, ChatThreadRow
from app.main import app

client = TestClient(app)

USER_ID = uuid.uuid4()
OTHER_USER_ID = uuid.uuid4()
THREAD_ID = uuid.uuid4()
NOW = datetime.now(UTC)


def _override_user() -> AuthenticatedUser:
    return AuthenticatedUser(id=USER_ID, email="user@example.com")


def _thread_row(user_id: uuid.UUID = USER_ID) -> ChatThreadRow:
    return ChatThreadRow(
        id=THREAD_ID,
        user_id=user_id,
        title="New chat",
        created_at=NOW,
        updated_at=NOW,
    )


def _message_row(role: str, sequence: int) -> ChatMessageRow:
    return ChatMessageRow(
        id=uuid.uuid4(),
        thread_id=THREAD_ID,
        role=role,
        content="Hello",
        parts=[{"type": "text", "text": "Hello"}],
        sequence=sequence,
        created_at=NOW,
    )


def test_list_threads_requires_auth() -> None:
    response = client.get("/chat/threads")
    assert response.status_code == 401


def test_list_threads_returns_threads() -> None:
    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_bearer_token] = lambda: "token"
    try:
        with (
            patch("app.api.chat.ensure_user"),
            patch("app.api.chat.create_user_client"),
            patch("app.api.chat.list_threads", return_value=[_thread_row()]),
        ):
            response = client.get(
                "/chat/threads",
                headers={"Authorization": "Bearer token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["id"] == str(THREAD_ID)
    assert payload[0]["title"] == "New chat"


def test_get_messages_returns_403_for_other_users_thread() -> None:
    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_bearer_token] = lambda: "token"
    try:
        with patch(
            "app.chat.access.get_thread_by_id",
            return_value=_thread_row(user_id=OTHER_USER_ID),
        ):
            response = client.get(
                f"/chat/threads/{THREAD_ID}/messages",
                headers={"Authorization": "Bearer token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_delete_thread_returns_204() -> None:
    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_bearer_token] = lambda: "token"
    try:
        with (
            patch("app.chat.access.get_thread_by_id", return_value=_thread_row()),
            patch("app.api.chat.create_user_client"),
            patch("app.api.chat.delete_thread") as delete_mock,
        ):
            response = client.delete(
                f"/chat/threads/{THREAD_ID}",
                headers={"Authorization": "Bearer token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    delete_mock.assert_called_once()


def test_delete_thread_returns_403_for_other_users_thread() -> None:
    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_bearer_token] = lambda: "token"
    try:
        with (
            patch(
                "app.chat.access.get_thread_by_id",
                return_value=_thread_row(user_id=OTHER_USER_ID),
            ),
            patch("app.api.chat.delete_thread") as delete_mock,
        ):
            response = client.delete(
                f"/chat/threads/{THREAD_ID}",
                headers={"Authorization": "Bearer token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    delete_mock.assert_not_called()


def test_stream_returns_event_stream() -> None:
    from collections.abc import AsyncIterator
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock

    from app.assistant.outputs import GroundedAnswer

    class _FakeStreamResult:
        async def stream_output(self) -> AsyncIterator[GroundedAnswer]:
            yield GroundedAnswer(
                answer="Grounded answer [1].",
                citations=[],
            )

        async def get_output(self) -> GroundedAnswer:
            return GroundedAnswer(answer="Grounded answer [1].", citations=[])

    @asynccontextmanager
    async def fake_run_stream(*_args, **_kwargs):
        yield _FakeStreamResult()

    @asynccontextmanager
    async def fake_session():
        yield AsyncMock()

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_bearer_token] = lambda: "token"
    try:
        with (
            patch("app.chat.orchestrator.require_thread_access", return_value=_thread_row()),
            patch("app.chat.orchestrator.ensure_user"),
            patch("app.chat.orchestrator.get_async_session", fake_session),
            patch("app.chat.orchestrator.document_agent.run_stream", fake_run_stream),
            patch("app.chat.orchestrator.validate_grounded_answer"),
            patch(
                "app.chat.orchestrator.normalize_grounded_answer",
                side_effect=lambda answer, _chunks: answer,
            ),
            patch(
                "app.chat.orchestrator.citation_parts",
                return_value=[{"type": "data-citation", "data": {"citationIndex": 1}}],
            ),
            patch("app.chat.orchestrator.append_messages"),
            patch("app.chat.orchestrator.append_citations"),
            patch("app.chat.orchestrator.create_user_client"),
        ):
            response = client.post(
                "/chat/stream",
                headers={"Authorization": "Bearer token"},
                json={
                    "id": str(THREAD_ID),
                    "messages": [
                        {
                            "id": "msg-1",
                            "role": "user",
                            "parts": [{"type": "text", "text": "Hi"}],
                        }
                    ],
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["x-vercel-ai-ui-message-stream"] == "v1"
    assert "text/event-stream" in response.headers["content-type"]
    assert '"type":"finish"' in response.text.replace(" ", "")
