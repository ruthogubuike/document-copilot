from ingest.chunking import (
    ChunkRecord,
    assert_embedding_dimensions,
    clean_markdown_tables,
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


def test_clean_markdown_tables_collapses_duplicate_label_columns() -> None:
    mangled = "\n".join(
        [
            "| Federal: | Federal: | Federal: |   |       |   |",
            "|----------|----------|----------|---|-------|---|",
            "| Current  | Current  | Current  | $ | 8,257 |   |",
            "| Total    | Total    | Total    |   | 1,081 |   |",
        ]
    )

    cleaned = clean_markdown_tables(mangled)

    assert cleaned.splitlines() == [
        "| Federal: |  |  |",
        "| --- | --- | --- |",
        "| Current | $ | 8,257 |",
        "| Total |  | 1,081 |",
    ]


def test_clean_markdown_tables_leaves_prose_untouched() -> None:
    prose = "Apple net sales grew.\n\nServices revenue increased year over year."

    assert clean_markdown_tables(prose) == prose


def test_clean_markdown_tables_ignores_pipe_text_without_separator() -> None:
    text = "Margins were strong | demand held up | guidance was raised."

    assert clean_markdown_tables(text) == text


def test_section_from_chunk_joins_headings() -> None:
    class FakeMeta:
        headings = ["PART I", "Item 1. Business"]

    class FakeChunk:
        meta = FakeMeta()

    assert section_from_chunk(FakeChunk()) == "PART I > Item 1. Business"
