from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.retrieval.retriever import HybridRetriever
from app.retrieval.types import RetrievedPassage


@dataclass
class DocumentAgentDeps:
    retriever: HybridRetriever
    session: AsyncSession
    retrieved_chunks: dict[uuid.UUID, RetrievedPassage] = field(default_factory=dict)
