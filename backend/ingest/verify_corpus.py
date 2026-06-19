"""Verify ingested corpus: chunks, embeddings, FTS, and retrieval smoke queries.

Usage:
    uv run python -m ingest.verify_corpus
"""

from __future__ import annotations

from sqlalchemy import create_engine, func, select, text

from app.config import settings
from app.database.models import DocumentChunk, SourceDocument
from app.retrieval.asyncio_compat import run_async
from app.retrieval.retriever import HybridRetriever
from app.retrieval.types import RetrievalFilters
from app.database.session import get_async_session

CLIENT_BRIEF_QUERIES = [
    ("AAPL revenue mix iPhone Services", "AAPL"),
    ("NVIDIA Data Center demand drivers", "NVDA"),
    ("Amazon AWS operating income margin", "AMZN"),
    ("Microsoft Azure AI infrastructure", "MSFT"),
    ("Alphabet Google Cloud revenue", "GOOGL"),
]


def verify_database() -> None:
    engine = create_engine(settings.sqlalchemy_database_url)
    with engine.connect() as conn:
        total_chunks = conn.execute(
            select(func.count()).select_from(DocumentChunk)
        ).scalar_one()
        docs_with_chunks = conn.execute(
            select(func.count(func.distinct(DocumentChunk.document_id)))
        ).scalar_one()
        missing_embedding = conn.execute(
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.embedding.is_(None))
        ).scalar_one()
        missing_fts = conn.execute(
            text(
                "SELECT count(*) FROM document_chunks WHERE search_vector IS NULL"
            )
        ).scalar_one()
        revenue_hits = conn.execute(
            text(
                """
                SELECT sd.ticker, sd.fiscal_year, dc.chunk_index, left(dc.text, 120)
                FROM document_chunks dc
                JOIN source_documents sd ON sd.id = dc.document_id
                WHERE sd.ticker = 'AAPL'
                  AND dc.text ILIKE '%iPhone%'
                  AND dc.text ILIKE '%Services%'
                LIMIT 3
                """
            )
        ).all()

    print(f"document_chunks: {total_chunks}")
    print(f"documents with chunks: {docs_with_chunks} / 25 expected")
    print(f"missing embeddings: {missing_embedding}")
    print(f"missing search_vector: {missing_fts}")

    if revenue_hits:
        print("\nApple revenue-mix spot check:")
        for ticker, year, index, preview in revenue_hits:
            print(f"  {ticker} FY{year} chunk {index}: {preview!r}...")
    else:
        print("\nWARNING: no Apple iPhone+Services spot-check hits")


async def verify_retrieval() -> None:
    retriever = HybridRetriever(top_k=3)
    print("\nClient-brief retrieval smoke:")
    async with get_async_session() as session:
        for query, ticker in CLIENT_BRIEF_QUERIES:
            passages = await retriever.retrieve(
                session,
                query,
                filters=RetrievalFilters(ticker=ticker),
            )
            if not passages:
                print(f"  FAIL {ticker}: no passages for {query!r}")
                continue
            preview = passages[0].text[:100].replace("\n", " ")
            print(f"  OK   {ticker}: {preview!r}...")


def main() -> None:
    verify_database()
    run_async(verify_retrieval())


if __name__ == "__main__":
    main()
