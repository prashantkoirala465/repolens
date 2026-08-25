import pytest

from repolens.retrieval import qdrant_store


class _FakeVectorParams:
    def __init__(self, size: int) -> None:
        self.size = size


class _FakeCollectionParams:
    def __init__(self, size: int) -> None:
        self.vectors = _FakeVectorParams(size)


class _FakeCollectionConfig:
    def __init__(self, size: int) -> None:
        self.params = _FakeCollectionParams(size)


class _FakeCollectionInfo:
    def __init__(self, size: int) -> None:
        self.config = _FakeCollectionConfig(size)


class _FakeQdrantClient:
    def __init__(self, existing_dim: int | None) -> None:
        self._existing_dim = existing_dim
        self.created_with: int | None = None

    def collection_exists(self, name: str) -> bool:
        return self._existing_dim is not None

    def get_collection(self, name: str) -> _FakeCollectionInfo:
        assert self._existing_dim is not None
        return _FakeCollectionInfo(self._existing_dim)

    def create_collection(self, collection_name: str, vectors_config: _FakeVectorParams) -> None:
        self.created_with = vectors_config.size


def test_ensure_collection_creates_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeQdrantClient(existing_dim=None)
    monkeypatch.setattr(qdrant_store, "_client", lambda: fake)

    qdrant_store.ensure_collection(768)

    assert fake.created_with == 768


def test_ensure_collection_is_a_noop_when_dimension_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeQdrantClient(existing_dim=1024)
    monkeypatch.setattr(qdrant_store, "_client", lambda: fake)

    qdrant_store.ensure_collection(1024)

    assert fake.created_with is None


def test_ensure_collection_raises_on_dimension_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeQdrantClient(existing_dim=1024)
    monkeypatch.setattr(qdrant_store, "_client", lambda: fake)

    with pytest.raises(ValueError, match="1024"):
        qdrant_store.ensure_collection(768)
