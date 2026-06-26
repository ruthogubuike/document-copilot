"""Manual smoke search against the ingested corpus.

Usage:
    uv run python -m app.retrieval.smoke_search "Apple iPhone Services revenue mix"
"""

from __future__ import annotations

import argparse
import sys

from app.database.session import get_async_session
from app.retrieval.asyncio_compat import run_async
from app.retrieval.retriever import HybridRetriever
from app.retrieval.types import RetrievalFilters


def _print_text(text: str) -> None:
    """Print safely on Windows consoles that default to cp1252."""
    encoding = sys.stdout.encoding or "utf-8"
    print(text.encode(encoding, errors="replace").decode(encoding))


async def run_smoke_search(query: str, *, ticker: str | None) -> None:
    retriever = HybridRetriever()
    filters = RetrievalFilters(ticker=ticker) if ticker else RetrievalFilters()

    async with get_async_session() as session:
        passages = await retriever.retrieve(session, query, filters=filters)

    if not passages:
        print("No passages found.")
        return

    print(f"Top {len(passages)} passage(s) for: {query!r}\n")
    for index, passage in enumerate(passages, start=1):
        print(f"--- {index}. {passage.ticker} FY{passage.fiscal_year} ---")
        print(f"section: {passage.section!r}")
        print(f"accession: {passage.accession_number}")
        _print_text(passage.text[:400])
        if passage.neighbor_chunks:
            print(f"neighbors: {len(passage.neighbor_chunks)}")
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test hybrid retrieval.")
    parser.add_argument("query", help="Search query text")
    parser.add_argument("--ticker", help="Optional ticker filter, e.g. AAPL")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_async(run_smoke_search(args.query, ticker=args.ticker))
