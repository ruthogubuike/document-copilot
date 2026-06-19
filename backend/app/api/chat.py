"""Chat thread CRUD and streaming endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth.dependencies import CurrentUser, get_bearer_token
from app.chat.access import require_thread_access
from app.chat.messages import UIMessage, message_row_to_ui
from app.chat.orchestrator import run_grounded_turn
from app.chat.streaming import STREAM_HEADERS
from app.database.chats import create_thread, list_messages, list_threads
from app.database.supabase import create_user_client
from app.database.users import ensure_user

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatThreadResponse(BaseModel):
    id: uuid.UUID
    title: str
    createdAt: datetime
    updatedAt: datetime


class CreateThreadRequest(BaseModel):
    title: str | None = None


class ThreadMessagesResponse(BaseModel):
    messages: list[UIMessage]


class StreamChatRequest(BaseModel):
    id: str
    messages: list[UIMessage]
    trigger: str | None = None
    messageId: str | None = None


def _thread_response(thread) -> ChatThreadResponse:
    return ChatThreadResponse(
        id=thread.id,
        title=thread.title,
        createdAt=thread.created_at,
        updatedAt=thread.updated_at,
    )


@router.get("/threads", response_model=list[ChatThreadResponse])
def get_threads(
    user: CurrentUser,
    token: str = Depends(get_bearer_token),
) -> list[ChatThreadResponse]:
    ensure_user(user)
    client = create_user_client(token)
    return [_thread_response(thread) for thread in list_threads(client)]


@router.post("/threads", response_model=ChatThreadResponse)
def post_thread(
    body: CreateThreadRequest,
    user: CurrentUser,
    token: str = Depends(get_bearer_token),
) -> ChatThreadResponse:
    ensure_user(user)
    client = create_user_client(token)
    thread = create_thread(
        client,
        user_id=user.id,
        title=body.title or "New chat",
    )
    return _thread_response(thread)


@router.get("/threads/{thread_id}/messages", response_model=ThreadMessagesResponse)
def get_thread_messages(
    thread_id: uuid.UUID,
    user: CurrentUser,
    token: str = Depends(get_bearer_token),
) -> ThreadMessagesResponse:
    require_thread_access(thread_id, user)
    client = create_user_client(token)
    rows = list_messages(client, thread_id)
    return ThreadMessagesResponse(messages=[message_row_to_ui(row) for row in rows])


@router.post("/stream")
async def stream_chat(
    body: StreamChatRequest,
    user: CurrentUser,
    token: str = Depends(get_bearer_token),
) -> StreamingResponse:
    try:
        thread_id = uuid.UUID(body.id)
    except ValueError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid thread id",
        ) from exc

    return StreamingResponse(
        run_grounded_turn(
            thread_id=thread_id,
            messages=body.messages,
            user=user,
            token=token,
        ),
        media_type="text/event-stream",
        headers=STREAM_HEADERS,
    )
