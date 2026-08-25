import httpx
import pytest

from repolens.generation.ollama_provider import OllamaGenerator
from repolens.retrieval.qdrant_store import RetrievedChunk


def _chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="a.py:1-5",
        file_path="a.py",
        start_line=1,
        end_line=5,
        text="def foo(): pass",
        symbol="foo",
        score=0.9,
    )


def test_generate_sends_json_schema_format_and_parses_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    def fake_post(self: httpx.Client, url: str, json: dict) -> httpx.Response:
        captured["url"] = url
        captured["payload"] = json
        body = {
            "message": {
                "content": '{"answer": "it does X", "cited_chunk_ids": ["a.py:1-5"]}',
            }
        }
        return httpx.Response(200, json=body, request=httpx.Request("POST", "http://test"))

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result = OllamaGenerator().generate("what does foo do?", [_chunk()])

    assert captured["url"] == "/api/chat"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["format"]["required"] == ["answer", "cited_chunk_ids"]
    assert result.answer == "it does X"
    assert result.cited_chunk_ids == ["a.py:1-5"]
