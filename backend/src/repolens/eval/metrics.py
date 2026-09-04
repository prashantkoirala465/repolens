"""Retrieval quality metrics: precision@k, recall@k, MRR, nDCG@k.

Every metric takes `matches`: for a ranked list of retrieved items,
`matches[i]` is the set of ground-truth relevant-span indices that item `i`
overlaps (empty if it doesn't overlap anything relevant), as produced by
`eval.relevance.judge_relevance`. Kept Qdrant/embedding-agnostic so these are
cheap to test exhaustively with plain data.
"""

import math
from collections.abc import Sequence


def precision_at_k(matches: Sequence[frozenset[int]], k: int) -> float:
    if k <= 0:
        return 0.0
    hits = sum(1 for m in matches[:k] if m)
    return hits / k


def recall_at_k(matches: Sequence[frozenset[int]], k: int, num_relevant: int) -> float:
    if num_relevant <= 0:
        return 0.0
    found: set[int] = set()
    for m in matches[:k]:
        found |= m
    return len(found) / num_relevant


def reciprocal_rank(matches: Sequence[frozenset[int]]) -> float:
    for rank, m in enumerate(matches, start=1):
        if m:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(matches: Sequence[frozenset[int]], k: int, num_relevant: int) -> float:
    """Novelty-discounted: a chunk only contributes gain the first time it
    surfaces a given relevant span. Without that, two different retrieved
    chunks legitimately overlapping the *same* labeled span (adjacent chunk
    boundaries do happen) could push DCG above the naive IDCG and out of
    [0, 1] — this keeps the metric bounded and rewards covering distinct
    relevant locations rather than re-surfacing one."""
    if num_relevant <= 0 or k <= 0:
        return 0.0
    seen: set[int] = set()
    dcg = 0.0
    for rank, m in enumerate(matches[:k], start=1):
        new_hits = m - seen
        if new_hits:
            dcg += 1.0 / math.log2(rank + 1)
            seen |= new_hits
    ideal_hits = min(k, num_relevant)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0
