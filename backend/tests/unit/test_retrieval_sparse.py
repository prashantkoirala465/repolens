import pytest

from repolens.retrieval.sparse import (
    _term_id,
    _tokenize,
    embed_sparse_documents,
    embed_sparse_query,
)


def test_tokenize_lowercases_and_splits_on_punctuation() -> None:
    assert _tokenize("Hello, WORLD!") == ["hello", "world"]


def test_tokenize_keeps_underscore_joined_identifiers_whole() -> None:
    assert _tokenize("foo-bar_baz.qux") == ["foo", "bar_baz", "qux"]


def test_tokenize_empty_text() -> None:
    assert _tokenize("") == []


def test_term_id_is_stable_across_calls() -> None:
    assert _term_id("session") == _term_id("session")


def test_term_id_differs_for_different_terms() -> None:
    ids = {_term_id(t) for t in ["session", "cookie", "adapter", "auth", "retry"]}
    assert len(ids) == 5


def test_term_id_fits_u32_range() -> None:
    for term in ["a", "session", "x" * 200, "123", "_"]:
        assert 0 <= _term_id(term) <= 2**32 - 1


def test_empty_document_yields_empty_sparse_vector() -> None:
    (vector,) = embed_sparse_documents([""])
    assert vector.indices == []
    assert vector.values == []


def test_empty_query_yields_empty_sparse_vector() -> None:
    vector = embed_sparse_query("")
    assert vector.indices == []
    assert vector.values == []


def test_single_document_corpus_saturates_to_exactly_one() -> None:
    # When a document's length equals the corpus average (trivially true for
    # a single-document batch) and a term appears once, BM25 saturation
    # reduces to (k1+1)/(k1+1) = 1.0 regardless of k1/b — a clean,
    # implementation-independent sanity check.
    (vector,) = embed_sparse_documents(["hello world"])
    assert vector.values == pytest.approx([1.0, 1.0])


def test_shorter_documents_get_higher_term_weight_than_longer_ones() -> None:
    # doc A is shorter than the corpus average, doc B longer — BM25's length
    # normalization should boost A's term weight relative to B's.
    doc_a, doc_b = embed_sparse_documents(["foo", "foo bar baz qux"])
    assert doc_a.values[0] > doc_b.values[0]


def test_saturation_matches_hand_computed_values() -> None:
    # avg_len = (1 + 4) / 2 = 2.5
    # doc A (len=1): length_norm = 1 - 0.75 + 0.75*(1/2.5) = 0.55
    #   saturated = (1*(1.2+1)) / (1 + 1.2*0.55) = 2.2 / 1.66 = 110/83
    # doc B (len=4): length_norm = 1 - 0.75 + 0.75*(4/2.5) = 1.45
    #   saturated = 2.2 / (1 + 1.2*1.45) = 2.2 / 2.74 = 110/137
    doc_a, doc_b = embed_sparse_documents(["foo", "foo bar baz qux"])
    assert doc_a.values[0] == pytest.approx(110 / 83)
    assert doc_b.values[0] == pytest.approx(110 / 137)


def test_document_and_query_use_the_same_term_index() -> None:
    # Retrieval only works if the same term hashes to the same index on
    # both the indexing side and the query side.
    (doc_vector,) = embed_sparse_documents(["session cookie"])
    query_vector = embed_sparse_query("session")
    assert query_vector.indices[0] in doc_vector.indices


def test_query_uses_raw_counts_not_saturation() -> None:
    query_vector = embed_sparse_query("session session cookie")
    values_by_index = dict(zip(query_vector.indices, query_vector.values, strict=True))
    session_index = embed_sparse_query("session").indices[0]
    assert values_by_index[session_index] == 2.0


def test_indices_and_values_are_parallel_and_sorted() -> None:
    (vector,) = embed_sparse_documents(["the quick brown fox jumps over the lazy dog"])
    assert len(vector.indices) == len(vector.values)
    assert vector.indices == sorted(vector.indices)
    assert len(vector.indices) == len(set(vector.indices))  # no duplicate terms


def test_embed_sparse_documents_preserves_batch_order() -> None:
    vectors = embed_sparse_documents(["alpha", "", "beta gamma"])
    assert len(vectors) == 3
    assert vectors[1].indices == []
