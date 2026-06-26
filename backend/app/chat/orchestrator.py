"""Coordinates one grounded chat turn: access check, agent, validate, stream, persist."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import structlog
from pydantic import ValidationError
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.usage import UsageLimits

from app.assistant.agent import document_agent
from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import GroundedAnswer
from app.auth.dependencies import AuthenticatedUser
from app.chat.access import require_thread_access
from app.chat.messages import (
    UIMessage,
    citation_parts,
    derive_thread_title,
    latest_user_message,
    messages_to_agent_history,
    text_parts,
    ui_message_to_persist,
)
from app.chat.streaming import (
    sse_citation_part,
    sse_done,
    sse_error,
    sse_finish,
    sse_start,
    sse_text_delta,
    sse_text_end,
    sse_text_start,
)
from app.config import settings
from app.database.chats import append_citations, append_messages
from app.database.session import get_async_session
from app.database.supabase import create_user_client
from app.database.users import ensure_user
from app.grounding.normalize import normalize_grounded_answer
from app.grounding.period import validate_period_alignment
from app.grounding.validator import GroundingError, validate_grounded_answer
from app.retrieval.retriever import HybridRetriever

logger = structlog.get_logger(__name__)


async def run_grounded_turn(
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
    history = messages_to_agent_history(messages)

    message_id = f"msg_{uuid.uuid4().hex}"
    text_id, text_start_event = sse_text_start()
    yield sse_start(message_id)
    yield text_start_event

    try:
        async with get_async_session() as session:
            deps = DocumentAgentDeps(
                retriever=HybridRetriever(),
                session=session,
                retrieved_chunks={},
            )
            async with document_agent.run_stream(
                user_text,
                deps=deps,
                message_history=history,
                usage_limits=UsageLimits(
                    tool_calls_limit=settings.agent_max_tool_calls
                ),
            ) as result:
                previous_answer = ""
                async for partial in result.stream_output():
                    if not isinstance(partial, GroundedAnswer):
                        continue
                    new_text = partial.answer
                    if len(new_text) > len(previous_answer):
                        delta = new_text[len(previous_answer) :]
                        previous_answer = new_text
                        yield sse_text_delta(text_id, delta)

                output = await result.get_output()

            output = normalize_grounded_answer(output, deps.retrieved_chunks)
            validate_grounded_answer(output, deps.retrieved_chunks)
            validate_period_alignment(user_text, output, deps.retrieved_chunks)

            citation_data_parts = citation_parts(output.citations, deps.retrieved_chunks)
            assistant_parts = text_parts(output.answer) + citation_data_parts

            yield sse_text_end(text_id)
            for part in citation_data_parts:
                yield sse_citation_part(part)
            yield sse_finish()

            client = create_user_client(token)
            _, assistant_row = append_messages(
                client,
                thread_id,
                user_content=user_text,
                user_parts=user_parts,
                assistant_content=output.answer,
                assistant_parts=assistant_parts,
                title=derive_thread_title(user_text),
            )
            append_citations(
                client,
                assistant_row.id,
                output.citations,
                deps.retrieved_chunks,
            )
    except (ValidationError, UnexpectedModelBehavior):
        yield sse_error(
            "The assistant returned an invalid answer format. Please try again."
        )
        yield sse_done()
        return
    except GroundingError as exc:
        yield sse_error(str(exc))
        yield sse_done()
        return
    except UsageLimitExceeded:
        yield sse_error(
            "This question required too many filing lookups. Try narrowing it "
            "(one company, one fiscal year, or a smaller comparison)."
        )
        yield sse_done()
        return
    except Exception:
        logger.exception(
            "grounded_chat_turn_failed",
            thread_id=str(thread_id),
            user_id=str(user.id),
        )
        yield sse_error("Failed to generate a grounded answer.")
        yield sse_done()
        return

    yield sse_done()
