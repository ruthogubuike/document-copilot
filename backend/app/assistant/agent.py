from __future__ import annotations

from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import GroundedAnswer
from app.assistant.tools import read_chunk, read_surrounding_chunks, search_filings
from app.config import settings

_INSTRUCTIONS_PATH = Path(__file__).with_name("instructions.md")


def load_instructions() -> str:
    return _INSTRUCTIONS_PATH.read_text(encoding="utf-8")


def build_document_agent() -> Agent[DocumentAgentDeps, GroundedAnswer]:
    model = OpenAIChatModel(
        settings.openai_chat_model,
        provider=OpenAIProvider(api_key=settings.openai_api_key),
    )
    agent: Agent[DocumentAgentDeps, GroundedAnswer] = Agent(
        model,
        deps_type=DocumentAgentDeps,
        output_type=GroundedAnswer,
        instructions=load_instructions(),
        defer_model_check=True,
    )
    agent.tool(search_filings)
    agent.tool(read_chunk)
    agent.tool(read_surrounding_chunks)
    return agent


document_agent = build_document_agent()
