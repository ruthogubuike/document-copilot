"""Thread ownership checks."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status

from app.auth.dependencies import AuthenticatedUser
from app.database.chats import ChatThreadRow, get_thread_by_id


def require_thread_access(
    thread_id: uuid.UUID,
    user: AuthenticatedUser,
) -> ChatThreadRow:
    thread = get_thread_by_id(thread_id)
    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )
    if thread.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this thread",
        )
    return thread
