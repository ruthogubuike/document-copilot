"""Chat thread and message persistence via Supabase."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from supabase import Client

from app.retrieval.types import RetrievedPassage


@dataclass(frozen=True, slots=True)
class ChatThreadRow:
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ChatMessageRow:
    id: uuid.UUID
    thread_id: uuid.UUID
    role: str
    content: str | None
    parts: list[dict[str, Any]] | None
    sequence: int
    created_at: datetime


def _parse_thread(row: dict[str, Any]) -> ChatThreadRow:
    return ChatThreadRow(
        id=uuid.UUID(row["id"]),
        user_id=uuid.UUID(row["user_id"]),
        title=row["title"],
        created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
        updated_at=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")),
    )


def _parse_message(row: dict[str, Any]) -> ChatMessageRow:
    return ChatMessageRow(
        id=uuid.UUID(row["id"]),
        thread_id=uuid.UUID(row["thread_id"]),
        role=row["role"],
        content=row.get("content"),
        parts=row.get("parts"),
        sequence=row["sequence"],
        created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
    )


def list_threads(client: Client) -> list[ChatThreadRow]:
    response = (
        client.table("chat_threads")
        .select("id, user_id, title, created_at, updated_at")
        .order("updated_at", desc=True)
        .execute()
    )
    return [_parse_thread(row) for row in response.data]


def create_thread(
    client: Client,
    *,
    user_id: uuid.UUID,
    title: str = "New chat",
) -> ChatThreadRow:
    thread_id = uuid.uuid4()
    response = (
        client.table("chat_threads")
        .insert(
            {
                "id": str(thread_id),
                "user_id": str(user_id),
                "title": title,
            }
        )
        .execute()
    )
    return _parse_thread(response.data[0])


def delete_thread(client: Client, thread_id: uuid.UUID) -> None:
    client.table("chat_threads").delete().eq("id", str(thread_id)).execute()


def get_thread_for_user(client: Client, thread_id: uuid.UUID) -> ChatThreadRow | None:
    response = (
        client.table("chat_threads")
        .select("id, user_id, title, created_at, updated_at")
        .eq("id", str(thread_id))
        .maybe_single()
        .execute()
    )
    if response.data is None:
        return None
    return _parse_thread(response.data)


def get_thread_by_id(thread_id: uuid.UUID) -> ChatThreadRow | None:
    from app.database.supabase import get_service_role_client

    client = get_service_role_client()
    response = (
        client.table("chat_threads")
        .select("id, user_id, title, created_at, updated_at")
        .eq("id", str(thread_id))
        .maybe_single()
        .execute()
    )
    if response.data is None:
        return None
    return _parse_thread(response.data)


def list_messages(client: Client, thread_id: uuid.UUID) -> list[ChatMessageRow]:
    response = (
        client.table("chat_messages")
        .select("id, thread_id, role, content, parts, sequence, created_at")
        .eq("thread_id", str(thread_id))
        .order("sequence")
        .execute()
    )
    return [_parse_message(row) for row in response.data]


def _next_sequence(client: Client, thread_id: uuid.UUID) -> int:
    response = (
        client.table("chat_messages")
        .select("sequence")
        .eq("thread_id", str(thread_id))
        .order("sequence", desc=True)
        .limit(1)
        .execute()
    )
    if not response.data:
        return 0
    return response.data[0]["sequence"] + 1


def append_messages(
    client: Client,
    thread_id: uuid.UUID,
    *,
    user_content: str,
    user_parts: list[dict[str, Any]],
    assistant_content: str,
    assistant_parts: list[dict[str, Any]],
    title: str | None = None,
) -> tuple[ChatMessageRow, ChatMessageRow]:
    base_sequence = _next_sequence(client, thread_id)
    rows = [
        {
            "id": str(uuid.uuid4()),
            "thread_id": str(thread_id),
            "role": "user",
            "content": user_content,
            "parts": user_parts,
            "sequence": base_sequence,
        },
        {
            "id": str(uuid.uuid4()),
            "thread_id": str(thread_id),
            "role": "assistant",
            "content": assistant_content,
            "parts": assistant_parts,
            "sequence": base_sequence + 1,
        },
    ]
    response = client.table("chat_messages").insert(rows).execute()
    user_row = _parse_message(response.data[0])
    assistant_row = _parse_message(response.data[1])
    thread_update: dict[str, Any] = {"updated_at": datetime.now(UTC).isoformat()}
    if title is not None and base_sequence == 0:
        thread_update["title"] = title
    client.table("chat_threads").update(thread_update).eq(
        "id", str(thread_id)
    ).execute()
    return user_row, assistant_row


def append_citations(
    client: Client,
    message_id: uuid.UUID,
    citations: list,
    passages: dict[uuid.UUID, RetrievedPassage],
) -> None:
    if not citations:
        return

    from app.assistant.outputs import Citation

    rows = []
    for citation in citations:
        if not isinstance(citation, Citation):
            raise TypeError("citations must be Citation instances")
        passage = passages[citation.chunk_id]
        rows.append(
            {
                "id": str(uuid.uuid4()),
                "message_id": str(message_id),
                "chunk_id": str(citation.chunk_id),
                "citation_index": citation.citation_index,
                "excerpt": citation.excerpt,
                "ticker": passage.ticker,
                "company_name": passage.company_name,
                "form": passage.form,
                "filing_date": passage.filing_date.isoformat(),
                "page": passage.page,
                "section": passage.section,
            }
        )

    client.table("message_citations").insert(rows).execute()
