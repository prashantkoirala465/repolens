import httpx

from repolens.core.config import get_settings


class OllamaEmbedder:
    """Embeds via a locally-running Ollama server — no API key, no cost.

    OLLAMA_EMBEDDING_MODEL is user-choosable, so unlike Voyage's fixed,
    known output size, this model's dimension isn't something we can hardcode.
    It's measured once (a single cheap local call) and cached for the process
    lifetime rather than re-probed per embed call.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client = httpx.Client(base_url=settings.ollama_base_url, timeout=120.0)
        self._model = settings.ollama_embedding_model
        self._dimension: int | None = None

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        response = self._client.post("/api/embed", json={"model": self._model, "input": texts})
        response.raise_for_status()
        embeddings: list[list[float]] = response.json()["embeddings"]
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            self._dimension = len(self.embed_query("repolens-dimension-probe"))
        return self._dimension
