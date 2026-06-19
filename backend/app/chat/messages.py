"""AI SDK UI message conversion."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

from app.assistant.outputs import Citation
from app.database.chats import ChatMessageRow
from app.retrieval.types import RetrievedPassage


class UIMessagePart(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    text: str | None = None


class UIMessage(BaseModel):
    id: str
    role: str
    parts: list[UIMessagePart] = Field(default_factory=list)


def text_parts(text: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": text}]


def extract_text_from_parts(parts: list[UIMessagePart]) -> str:
    chunks: list[str] = []
    for part in parts:
        if part.type == "text" and part.text:
            chunks.append(part.text)
    return "".join(chunks).strip()


def latest_user_message(messages: list[UIMessage]) -> UIMessage:
    for message in reversed(messages):
        if message.role == "user":
            return message
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Request must include at least one user message",
    )


def message_row_to_ui(row: ChatMessageRow) -> UIMessage:
    if row.parts:
        parts = [UIMessagePart(**part) for part in row.parts]
    elif row.content:
        parts = [UIMessagePart(type="text", text=row.content)]
    else:
        parts = []
    return UIMessage(id=str(row.id), role=row.role, parts=parts)


def ui_message_to_persist(message: UIMessage) -> tuple[str, list[dict[str, Any]]]:
    content = extract_text_from_parts(message.parts)
    parts = [part.model_dump(exclude_none=True) for part in message.parts]
    if not parts and content:
        parts = text_parts(content)
    return content, parts


def new_message_id() -> str:
    return str(uuid.uuid4())


def citation_parts(
    citations: list[Citation],
    passages: dict[uuid.UUID, RetrievedPassage],
) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    for citation in citations:
        passage = passages[citation.chunk_id]
        parts.append(
            {
                "type": "data-citation",
                "data": {
                    "citationIndex": citation.citation_index,
                    "chunkId": str(citation.chunk_id),
                    "ticker": passage.ticker,
                    "companyName": passage.company_name,
                    "form": passage.form,
                    "filingDate": passage.filing_date.isoformat(),
                    "page": passage.page,
                    "section": passage.section,
                    "excerpt": citation.excerpt,
                },
            }
        )
    return parts


def messages_to_agent_history(messages: list[UIMessage]) -> list[ModelMessage]:
    prior = messages[:-1] if messages and messages[-1].role == "user" else messages

    history: list[ModelMessage] = []
    for message in prior:
        text = extract_text_from_parts(message.parts)
        if not text:
            continue
        if message.role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=text)]))
        elif message.role == "assistant":
            history.append(ModelResponse(parts=[TextPart(content=text)]))
    return history
