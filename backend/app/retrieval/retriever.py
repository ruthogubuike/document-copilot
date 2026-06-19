from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.retrieval.embed_query import embed_query
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.queries import (
    fetch_neighbor_passages,
    fetch_passages_by_ids,
    fulltext_search_ids,
    semantic_search_ids,
)
from app.retrieval.types import RetrievedPassage, RetrievalFilters


class HybridRetriever:
    def __init__(
        self,
        *,
        candidate_k: int | None = None,
        top_k: int | None = None,
        rrf_k: int | None = None,
        neighbor_window: int | None = None,
    ) -> None:
        self.candidate_k = (
            settings.retrieval_candidate_k if candidate_k is None else candidate_k
        )
        self.top_k = settings.retrieval_top_k if top_k is None else top_k
        self.rrf_k = settings.retrieval_rrf_k if rrf_k is None else rrf_k
        self.neighbor_window = (
            settings.retrieval_neighbor_window
            if neighbor_window is None
            else neighbor_window
        )

    async def retrieve(
        self,
        session: AsyncSession,
        query: str,
        *,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievedPassage]:
        filters = filters or RetrievalFilters()
        query_embedding = await asyncio.to_thread(embed_query, query)

        semantic_ids = await semantic_search_ids(
            session,
            query_embedding,
            filters=filters,
            limit=self.candidate_k,
        )
        fulltext_ids = await fulltext_search_ids(
            session,
            query,
            filters=filters,
            limit=self.candidate_k,
        )

        if not semantic_ids and not fulltext_ids:
            return []

        fused = reciprocal_rank_fusion(
            [semantic_ids, fulltext_ids],
            k=self.rrf_k,
        )[: self.top_k]

        passage_map = await fetch_passages_by_ids(
            session,
            [chunk_id for chunk_id, _score in fused],
        )

        results: list[RetrievedPassage] = []
        for chunk_id, _score in fused:
            passage = passage_map.get(chunk_id)
            if passage is None:
                continue
            neighbors = await fetch_neighbor_passages(
                session,
                document_id=passage.document_id,
                chunk_index=passage.chunk_index,
                window=self.neighbor_window,
                exclude_chunk_id=passage.chunk_id,
            )
            results.append(passage.model_copy(update={"neighbor_chunks": neighbors}))

        return results

    async def read_chunk(
        self,
        session: AsyncSession,
        chunk_id: uuid.UUID,
    ) -> RetrievedPassage | None:
        from app.retrieval.queries import fetch_passage_by_id

        return await fetch_passage_by_id(session, chunk_id)

    async def read_surrounding_chunks(
        self,
        session: AsyncSession,
        chunk_id: uuid.UUID,
        *,
        window: int | None = None,
    ) -> list[RetrievedPassage]:
        from app.retrieval.queries import fetch_passage_by_id

        passage = await fetch_passage_by_id(session, chunk_id)
        if passage is None:
            return []

        neighbor_window = window if window is not None else self.neighbor_window
        center = await fetch_passage_by_id(session, chunk_id)
        if center is None:
            return []

        neighbors = await fetch_neighbor_passages(
            session,
            document_id=center.document_id,
            chunk_index=center.chunk_index,
            window=neighbor_window,
            exclude_chunk_id=None,
        )
        return [center, *[n for n in neighbors if n.chunk_id != center.chunk_id]]
