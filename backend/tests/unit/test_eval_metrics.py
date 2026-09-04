import math

import pytest

from repolens.eval.metrics import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank

_EMPTY = frozenset[int]()


def test_precision_at_k_all_relevant() -> None:
    matches = [frozenset({0}), frozenset({0}), frozenset({0})]
    assert precision_at_k(matches, 3) == 1.0


def test_precision_at_k_none_relevant() -> None:
    matches = [_EMPTY, _EMPTY]
    assert precision_at_k(matches, 2) == 0.0


def test_precision_at_k_partial() -> None:
    matches = [_EMPTY, frozenset({0})]
    assert precision_at_k(matches, 2) == 0.5


def test_precision_at_k_only_considers_top_k() -> None:
    matches = [frozenset({0}), _EMPTY, _EMPTY]
    assert precision_at_k(matches, 1) == 1.0


def test_precision_at_k_shorter_list_than_k_dilutes_the_score() -> None:
    matches = [frozenset({0})]
    assert precision_at_k(matches, 5) == 1 / 5


def test_precision_at_k_zero_k_is_zero() -> None:
    assert precision_at_k([frozenset({0})], 0) == 0.0


def test_recall_at_k_finds_all_distinct_spans() -> None:
    matches = [frozenset({0}), frozenset({1})]
    assert recall_at_k(matches, 2, num_relevant=2) == 1.0


def test_recall_at_k_partial_coverage() -> None:
    matches = [frozenset({0}), _EMPTY, _EMPTY]
    assert recall_at_k(matches, 3, num_relevant=3) == pytest.approx(1 / 3)


def test_recall_at_k_does_not_double_count_repeated_span_hits() -> None:
    matches = [frozenset({0}), frozenset({0}), frozenset({0})]
    assert recall_at_k(matches, 3, num_relevant=1) == 1.0


def test_recall_at_k_zero_relevant_is_zero() -> None:
    assert recall_at_k([frozenset({0})], 5, num_relevant=0) == 0.0


def test_recall_at_k_respects_cutoff() -> None:
    matches = [_EMPTY, frozenset({0})]
    assert recall_at_k(matches, 1, num_relevant=1) == 0.0


def test_reciprocal_rank_first_hit() -> None:
    matches = [frozenset({0}), _EMPTY]
    assert reciprocal_rank(matches) == 1.0


def test_reciprocal_rank_later_hit() -> None:
    matches = [_EMPTY, frozenset({0})]
    assert reciprocal_rank(matches) == 0.5


def test_reciprocal_rank_no_hit_is_zero() -> None:
    matches = [_EMPTY, _EMPTY]
    assert reciprocal_rank(matches) == 0.0


def test_reciprocal_rank_empty_list_is_zero() -> None:
    assert reciprocal_rank([]) == 0.0


def test_ndcg_perfect_ranking_is_one() -> None:
    matches = [frozenset({0}), frozenset({1})]
    assert ndcg_at_k(matches, 2, num_relevant=2) == pytest.approx(1.0)


def test_ndcg_no_hits_is_zero() -> None:
    matches = [_EMPTY, _EMPTY]
    assert ndcg_at_k(matches, 2, num_relevant=2) == 0.0


def test_ndcg_rewards_earlier_hits() -> None:
    early = [frozenset({0}), _EMPTY]
    late = [_EMPTY, frozenset({0})]
    assert ndcg_at_k(early, 2, num_relevant=1) > ndcg_at_k(late, 2, num_relevant=1)


def test_ndcg_matches_hand_computed_value() -> None:
    # rank 1 misses, rank 2 hits: dcg = 1/log2(3); ideal (1 relevant span) = 1/log2(2) = 1
    matches = [_EMPTY, frozenset({0})]
    expected = (1.0 / math.log2(3)) / 1.0
    assert ndcg_at_k(matches, 2, num_relevant=1) == pytest.approx(expected)


def test_ndcg_repeated_span_hits_do_not_exceed_one() -> None:
    # two different chunks both legitimately overlap the same labeled span —
    # the second shouldn't get fresh credit, or nDCG would exceed 1.0
    matches = [frozenset({0}), frozenset({0}), frozenset({0})]
    assert ndcg_at_k(matches, 3, num_relevant=1) == pytest.approx(1.0)


def test_ndcg_zero_relevant_is_zero() -> None:
    assert ndcg_at_k([frozenset({0})], 3, num_relevant=0) == 0.0


def test_ndcg_zero_k_is_zero() -> None:
    assert ndcg_at_k([frozenset({0})], 0, num_relevant=1) == 0.0


def test_ndcg_empty_matches_list() -> None:
    assert ndcg_at_k([], 5, num_relevant=1) == 0.0
