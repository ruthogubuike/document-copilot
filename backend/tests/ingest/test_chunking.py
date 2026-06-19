from ingest.chunking import (
    ChunkRecord,
    assert_embedding_dimensions,
    section_from_chunk,
)
from ingest.load_chunks import chunk_records_to_rows


def test_assert_embedding_dimensions() -> None:
    vector = assert_embedding_dimensions([0.1] * 1536)
    assert len(vector) == 1536


def test_chunk_records_to_rows_pairs_embeddings() -> None:
    records = [
        ChunkRecord(
            chunk_index=0,
            text="Apple revenue grew.",
            token_count=4,
            page="12",
            section="Item 7",
            chunk_metadata={"ticker": "AAPL"},
        )
    ]
    embeddings = [[0.5] * 1536]

    rows = chunk_records_to_rows(records, embeddings)

    assert rows[0]["text"] == "Apple revenue grew."
    assert rows[0]["embedding"] == embeddings[0]
    assert rows[0]["section"] == "Item 7"


def test_section_from_chunk_joins_headings() -> None:
    class FakeMeta:
        headings = ["PART I", "Item 1. Business"]

    class FakeChunk:
        meta = FakeMeta()

    assert section_from_chunk(FakeChunk()) == "PART I > Item 1. Business"
