import pytest

from repolens.retrieval import qdrant_store


class _FakeVectorParams:
    def __init__(self, size: int) -> None:
        self.size = size


class _FakeCollectionParams:
    def __init__(self, dense_size: int, has_sparse: bool) -> None:
        self.vectors = {"dense": _FakeVectorParams(dense_size)}
        self.sparse_vectors = {"bm25": object()} if has_sparse else {}


class _FakeCollectionConfig:
    def __init__(self, dense_size: int, has_sparse: bool) -> None:
        self.params = _FakeCollectionParams(dense_size, has_sparse)


class _FakeCollectionInfo:
    def __init__(self, dense_size: int, has_sparse: bool) -> None:
        self.config = _FakeCollectionConfig(dense_size, has_sparse)


class _FakeQdrantClient:
    def __init__(self, existing_dim: int | None, existing_has_sparse: bool = True) -> None:
        self._existing_dim = existing_dim
        self._existing_has_sparse = existing_has_sparse
        self.created_with: dict[str, object] | None = None

    def collection_exists(self, name: str) -> bool:
        return self._existing_dim is not None

    def get_collection(self, name: str) -> _FakeCollectionInfo:
        assert self._existing_dim is not None
        return _FakeCollectionInfo(self._existing_dim, self._existing_has_sparse)

    def create_collection(
        self, collection_name: str, vectors_config: dict, sparse_vectors_config: dict
    ) -> None:
        self.created_with = {
            "vectors_config": vectors_config,
            "sparse_vectors_config": sparse_vectors_config,
        }


def test_ensure_collection_creates_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeQdrantClient(existing_dim=None)
    monkeypatch.setattr(qdrant_store, "_client", lambda: fake)

    qdrant_store.ensure_collection(768)

    assert fake.created_with is not None
    assert fake.created_with["vectors_config"]["dense"].size == 768
    assert "bm25" in fake.created_with["sparse_vectors_config"]


def test_ensure_collection_is_a_noop_when_schema_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeQdrantClient(existing_dim=1024, existing_has_sparse=True)
    monkeypatch.setattr(qdrant_store, "_client", lambda: fake)

    qdrant_store.ensure_collection(1024)

    assert fake.created_with is None


def test_ensure_collection_raises_on_dimension_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeQdrantClient(existing_dim=1024, existing_has_sparse=True)
    monkeypatch.setattr(qdrant_store, "_client", lambda: fake)

    with pytest.raises(ValueError, match="1024"):
        qdrant_store.ensure_collection(768)


def test_ensure_collection_raises_when_sparse_vector_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # a collection from before hybrid retrieval: right dense dimension, but
    # no "bm25" sparse vector configured at all
    fake = _FakeQdrantClient(existing_dim=768, existing_has_sparse=False)
    monkeypatch.setattr(qdrant_store, "_client", lambda: fake)

    with pytest.raises(ValueError, match="doesn't match the expected schema"):
        qdrant_store.ensure_collection(768)
