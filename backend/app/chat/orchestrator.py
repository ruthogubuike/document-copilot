"""Coordinates one stubbed chat turn: access check, stream, persist."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from app.auth.dependencies import AuthenticatedUser
from app.chat.access import require_thread_access
from app.chat.messages import (
    UIMessage,
    latest_user_message,
    text_parts,
    ui_message_to_persist,
)
from app.chat.streaming import stream_stub_reply
from app.database.chats import append_messages
from app.database.supabase import create_user_client
from app.database.users import ensure_user

STUB_PREFIX = "Stub response — retrieval not wired yet."


def build_stub_reply(user_text: str) -> str:
    if user_text:
        return f'{STUB_PREFIX} You said: "{user_text}"'
    return STUB_PREFIX


async def run_stub_turn(
    *,
    thread_id: uuid.UUID,
    messages: list[UIMessage],
    user: AuthenticatedUser,
    token: str,
) -> AsyncIterator[str]:
    require_thread_access(thread_id, user)
    ensure_user(user)

    user_message = latest_user_message(messages)
    user_text, user_parts = ui_message_to_persist(user_message)
    reply_text = build_stub_reply(user_text)

    async for chunk in stream_stub_reply(reply_text):
        yield chunk

    client = create_user_client(token)
    append_messages(
        client,
        thread_id,
        user_content=user_text,
        user_parts=user_parts,
        assistant_content=reply_text,
        assistant_parts=text_parts(reply_text),
    )
