import httpx
import pytest

from repolens.embeddings.ollama import OllamaEmbedder


def _fake_response(payload: dict) -> httpx.Response:
    return httpx.Response(200, json=payload, request=httpx.Request("POST", "http://test"))


def test_embed_documents_posts_model_and_input(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_post(self: httpx.Client, url: str, json: dict) -> httpx.Response:
        captured["url"] = url
        captured["json"] = json
        return _fake_response({"embeddings": [[0.1, 0.2], [0.3, 0.4]]})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    vectors = OllamaEmbedder().embed_documents(["a", "b"])

    assert captured["url"] == "/api/embed"
    assert captured["json"]["input"] == ["a", "b"]
    assert vectors == [[0.1, 0.2], [0.3, 0.4]]


def test_embed_query_returns_single_vector(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        httpx.Client,
        "post",
        lambda self, url, json: _fake_response({"embeddings": [[1.0, 2.0, 3.0]]}),
    )

    assert OllamaEmbedder().embed_query("hello") == [1.0, 2.0, 3.0]


def test_dimension_is_probed_once_and_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = 0

    def fake_post(self: httpx.Client, url: str, json: dict) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return _fake_response({"embeddings": [[0.0] * 5]})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    embedder = OllamaEmbedder()
    assert embedder.dimension == 5
    assert embedder.dimension == 5
    assert call_count == 1
