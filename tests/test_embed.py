import numpy as np
import pytest
from storage.embed import embed_texts


def test_embed_texts_float32_roundtrip(mocker):
    mock_embedder = mocker.MagicMock()
    mock_embedder.embed_documents.return_value = [[0.1, 0.2, 0.3]]
    mocker.patch("storage.embed.VoyageAIEmbeddings", return_value=mock_embedder)

    result = embed_texts(["some text"], api_key="test-key")

    decoded = np.frombuffer(result[0], dtype=np.float32)
    assert np.allclose(decoded, [0.1, 0.2, 0.3], atol=1e-6)


def test_embed_texts_one_bytes_per_text(mocker):
    vectors = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
    mock_embedder = mocker.MagicMock()
    mock_embedder.embed_documents.return_value = vectors
    mocker.patch("storage.embed.VoyageAIEmbeddings", return_value=mock_embedder)

    result = embed_texts(["a", "b", "c"], api_key="test-key")

    assert len(result) == 3
    assert all(isinstance(b, bytes) for b in result)


def test_embed_texts_empty_input(mocker):
    mock_embedder = mocker.MagicMock()
    mock_embedder.embed_documents.return_value = []
    mocker.patch("storage.embed.VoyageAIEmbeddings", return_value=mock_embedder)

    result = embed_texts([], api_key="test-key")

    assert result == []
