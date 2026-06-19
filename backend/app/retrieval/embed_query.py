from __future__ import annotations

from ingest.embeddings import embed_texts


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
