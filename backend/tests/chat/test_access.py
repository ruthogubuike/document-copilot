"""Unit tests for thread ownership checks."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.auth.dependencies import AuthenticatedUser
from app.chat.access import require_thread_access
from app.database.chats import ChatThreadRow


def _thread_for(user_id: uuid.UUID) -> ChatThreadRow:
    now = datetime.now(UTC)
    return ChatThreadRow(
        id=uuid.uuid4(),
        user_id=user_id,
        title="Test",
        created_at=now,
        updated_at=now,
    )


def test_require_thread_access_returns_thread_for_owner() -> None:
    user_id = uuid.uuid4()
    thread = _thread_for(user_id)
    user = AuthenticatedUser(id=user_id, email="owner@example.com")

    with patch("app.chat.access.get_thread_by_id", return_value=thread):
        result = require_thread_access(thread.id, user)

    assert result == thread


def test_require_thread_access_raises_404_when_missing() -> None:
    user = AuthenticatedUser(id=uuid.uuid4(), email="user@example.com")

    with patch("app.chat.access.get_thread_by_id", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            require_thread_access(uuid.uuid4(), user)

    assert exc_info.value.status_code == 404


def test_require_thread_access_raises_403_for_other_user() -> None:
    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()
    thread = _thread_for(owner_id)
    user = AuthenticatedUser(id=other_id, email="other@example.com")

    with patch("app.chat.access.get_thread_by_id", return_value=thread):
        with pytest.raises(HTTPException) as exc_info:
            require_thread_access(thread.id, user)

    assert exc_info.value.status_code == 403
