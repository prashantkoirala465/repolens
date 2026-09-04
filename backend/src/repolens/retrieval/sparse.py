"""BM25-style sparse vectors for hybrid retrieval.

Term-frequency saturation (the `k1`/`b` half of BM25) is computed here;
IDF weighting is Qdrant's job (`SparseVectorParams(modifier=Modifier.IDF)`
on the collection), computed server-side from indexed term
document-frequencies. That split is why the client only ever needs a
tokenizer and term counts, not a corpus-wide IDF table of its own.

No new dependency for this: a general sparse-embedding library (e.g.
fastembed's `Qdrant/bm25` model, Qdrant's own reference implementation for
this exact integration) pulls in onnxruntime and Pillow unconditionally —
infrastructure for neural embedders this project never uses, just to count
words. Tokenization is a plain word-boundary regex and the term->index
mapping is stdlib `hashlib`.

One advantage over a stateless per-document library: `embed_sparse_documents`
receives a whole repo's chunks in one batch (services/indexer.py,
eval/runner.py already work this way), so `avgdl` here is this corpus's
real average chunk length, not a fixed constant approximation.
"""

import hashlib
import re
from collections import Counter
from collections.abc import Sequence

from qdrant_client.models import SparseVector

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_BM25_K1 = 1.2
_BM25_B = 0.75


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _term_id(term: str) -> int:
    """Stable across process restarts, unlike Python's per-process-randomized
    hash(). Truncated to 4 bytes because Qdrant's sparse vector indices are
    u32 — the same hashing-trick collision exposure any hash-based sparse
    space has (including fastembed's own mmh3-based scheme), not something
    specific to this implementation."""
    digest = hashlib.blake2b(term.encode("utf-8"), digest_size=4).digest()
    return int.from_bytes(digest, "big")


def _to_sparse_vector(term_counts: dict[str, float]) -> SparseVector:
    if not term_counts:
        return SparseVector(indices=[], values=[])
    entries = sorted((_term_id(term), value) for term, value in term_counts.items())
    return SparseVector(indices=[i for i, _ in entries], values=[v for _, v in entries])


def embed_sparse_documents(texts: Sequence[str]) -> list[SparseVector]:
    """BM25 term-frequency saturation using this batch's real average
    document length — see module docstring."""
    token_lists = [_tokenize(t) for t in texts]
    lengths = [len(tokens) for tokens in token_lists]
    avg_len = sum(lengths) / len(lengths) if lengths else 0.0

    vectors: list[SparseVector] = []
    for tokens, length in zip(token_lists, lengths, strict=True):
        if not tokens:
            vectors.append(SparseVector(indices=[], values=[]))
            continue
        length_norm = (1 - _BM25_B + _BM25_B * (length / avg_len)) if avg_len else 1.0
        saturated = {
            term: (freq * (_BM25_K1 + 1)) / (freq + _BM25_K1 * length_norm)
            for term, freq in Counter(tokens).items()
        }
        vectors.append(_to_sparse_vector(saturated))
    return vectors


def embed_sparse_query(text: str) -> SparseVector:
    """Raw term counts, not saturated — BM25 only saturates the document
    side; the query vector just selects which terms to sum via Qdrant's
    sparse dot product."""
    counts = Counter(_tokenize(text))
    return _to_sparse_vector({term: float(count) for term, count in counts.items()})
