from voyageai.client import Client as VoyageClient

from repolens.core.config import get_settings

# voyage-code-3's fixed output size. Hardcoded rather than probed at runtime
# (contrast OllamaEmbedder) because probing would burn a paid API call for a
# value that's already documented and fixed per model.
_DIMENSION = 1024


class VoyageEmbedder:
    """Thin wrapper around the Voyage client, batched.

    voyage-code-3 over OpenAI text-embedding-3-large: the deciding factor
    was code-retrieval benchmark performance, not price.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client = VoyageClient(api_key=settings.voyage_api_key)
        self._model = settings.voyage_model
        self._batch_size = settings.embedding_batch_size

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            result = self._client.embed(batch, model=self._model, input_type="document")
            vectors.extend([float(x) for x in embedding] for embedding in result.embeddings)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        result = self._client.embed([text], model=self._model, input_type="query")
        return [float(x) for x in result.embeddings[0]]

    @property
    def dimension(self) -> int:
        return _DIMENSION
