"""Verify ingested corpus: chunks, embeddings, FTS, and retrieval smoke queries.

Usage:
    uv run python -m ingest.verify_corpus
"""

from __future__ import annotations

from sqlalchemy import create_engine, func, select, text

from app.config import settings
from app.database.models import DocumentChunk
from app.database.session import get_async_session
from app.retrieval.asyncio_compat import run_async
from app.retrieval.retriever import HybridRetriever
from app.retrieval.types import RetrievalFilters

CLIENT_BRIEF_QUERIES: list[tuple[str, str | None, tuple[str, ...]]] = [
    (
        "Apple 2021 2025 revenue mix iPhone Services Mac iPad Wearables",
        "AAPL",
        ("iphone", "services", "mac", "ipad", "wearables"),
    ),
    (
        "Amazon AWS operating income margin North America International 2021 2025",
        "AMZN",
        ("aws", "operating income", "north america", "international"),
    ),
    (
        "NVIDIA Data Center demand drivers customer concentration supply constraints",
        "NVDA",
        ("data center", "supply", "customer"),
    ),
    (
        "Microsoft Azure AI infrastructure cloud capacity constraints",
        "MSFT",
        ("azure", "cloud", "capacity"),
    ),
    (
        "Alphabet Google Search YouTube ads Google Network subscriptions devices Google Cloud revenue",
        "GOOGL",
        ("google search", "youtube", "google cloud"),
    ),
    (
        "AI cloud infrastructure export controls supply chain regulation risk factors",
        None,
        ("risk", "ai", "regulation"),
    ),
    (
        "Apple NVIDIA supplier concentration third-party manufacturing",
        None,
        ("supplier", "manufacturing"),
    ),
    (
        "Microsoft Alphabet Amazon NVIDIA capital expenditures purchase commitments AI cloud infrastructure",
        None,
        ("capital expenditures", "purchase commitments"),
    ),
    (
        "geographic revenue exposures latest 10-K year-over-year changes",
        None,
        ("geographic", "revenue"),
    ),
    (
        "generative AI improved margins evidence filings refuse infer beyond filings",
        None,
        ("margin", "ai"),
    ),
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
    retriever = HybridRetriever(top_k=5)
    print("\nClient-brief retrieval smoke:")
    async with get_async_session() as session:
        for query, ticker, expected_terms in CLIENT_BRIEF_QUERIES:
            filters = RetrievalFilters(ticker=ticker) if ticker else RetrievalFilters()
            passages = await retriever.retrieve(
                session,
                query,
                filters=filters,
            )
            if not passages:
                label = ticker or "ALL"
                print(f"  FAIL {label}: no passages for {query!r}")
                continue
            evidence_parts: list[str] = []
            for passage in passages:
                evidence_parts.append(passage.text)
                evidence_parts.extend(
                    neighbor.text for neighbor in passage.neighbor_chunks
                )
            evidence_text = "\n".join(evidence_parts).lower()
            missing_terms = [
                term for term in expected_terms if term not in evidence_text
            ]
            preview = passages[0].text[:100].replace("\n", " ")
            label = ticker or "ALL"
            if missing_terms:
                print(
                    f"  WARN {label}: missing {missing_terms!r} in top evidence for {query!r}"
                )
                print(f"       top preview: {preview!r}...")
            else:
                print(f"  OK   {label}: {preview!r}...")


def main() -> None:
    verify_database()
    run_async(verify_retrieval())


if __name__ == "__main__":
    main()
