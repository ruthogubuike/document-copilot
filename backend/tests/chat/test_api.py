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


def test_stream_returns_event_stream() -> None:
    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_bearer_token] = lambda: "token"
    try:
        with (
            patch("app.chat.orchestrator.require_thread_access", return_value=_thread_row()),
            patch("app.chat.orchestrator.ensure_user"),
            patch("app.chat.orchestrator.append_messages"),
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
