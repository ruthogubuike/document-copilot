from __future__ import annotations

from openai import OpenAI

from app.config import settings
from ingest.chunking import (
    EMBED_BATCH_SIZE,
    assert_embedding_dimensions,
)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    client = OpenAI(api_key=settings.openai_api_key)
    embeddings: list[list[float]] = []

    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start : start + EMBED_BATCH_SIZE]
        response = client.embeddings.create(
            model=settings.openai_embedding_model,
            input=batch,
            dimensions=settings.openai_embedding_dimensions,
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        embeddings.extend(
            assert_embedding_dimensions(list(item.embedding)) for item in ordered
        )

    return embeddings
