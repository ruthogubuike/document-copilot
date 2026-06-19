from unittest.mock import MagicMock, patch

from ingest.embeddings import embed_texts


@patch("ingest.embeddings.OpenAI")
def test_embed_texts_batches_and_returns_vectors(mock_openai_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.embeddings.create.return_value = MagicMock(
        data=[
            MagicMock(index=0, embedding=[0.1] * 1536),
            MagicMock(index=1, embedding=[0.2] * 1536),
        ]
    )

    vectors = embed_texts(["first chunk", "second chunk"])

    assert len(vectors) == 2
    assert len(vectors[0]) == 1536
    mock_client.embeddings.create.assert_called_once()
