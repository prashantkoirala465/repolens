from dataclasses import dataclass

from repolens.eval.relevance import judge_relevance


@dataclass(frozen=True, slots=True)
class _Span:
    file_path: str
    start_line: int
    end_line: int


def test_exact_match_overlaps() -> None:
    retrieved = [_Span("a.py", 10, 20)]
    spans = [_Span("a.py", 10, 20)]
    assert judge_relevance(retrieved, spans) == [frozenset({0})]


def test_partial_overlap_counts() -> None:
    retrieved = [_Span("a.py", 15, 25)]
    spans = [_Span("a.py", 10, 20)]
    assert judge_relevance(retrieved, spans) == [frozenset({0})]


def test_touching_boundary_counts_as_overlap() -> None:
    # inclusive line ranges: chunk ending exactly where the span starts shares a line
    retrieved = [_Span("a.py", 1, 10)]
    spans = [_Span("a.py", 10, 20)]
    assert judge_relevance(retrieved, spans) == [frozenset({0})]


def test_disjoint_line_ranges_do_not_overlap() -> None:
    retrieved = [_Span("a.py", 1, 9)]
    spans = [_Span("a.py", 10, 20)]
    assert judge_relevance(retrieved, spans) == [frozenset()]


def test_same_lines_different_file_do_not_overlap() -> None:
    retrieved = [_Span("b.py", 10, 20)]
    spans = [_Span("a.py", 10, 20)]
    assert judge_relevance(retrieved, spans) == [frozenset()]


def test_one_chunk_can_match_multiple_spans() -> None:
    retrieved = [_Span("a.py", 1, 100)]
    spans = [_Span("a.py", 10, 20), _Span("a.py", 50, 60), _Span("b.py", 10, 20)]
    assert judge_relevance(retrieved, spans) == [frozenset({0, 1})]


def test_rank_order_and_multiple_chunks_matching_one_span() -> None:
    retrieved = [
        _Span("a.py", 1, 5),  # no match
        _Span("a.py", 8, 12),  # matches span 0
        _Span("a.py", 9, 11),  # also matches span 0 (overlapping chunk boundaries)
    ]
    spans = [_Span("a.py", 10, 20)]
    assert judge_relevance(retrieved, spans) == [
        frozenset(),
        frozenset({0}),
        frozenset({0}),
    ]


def test_empty_retrieved_list() -> None:
    assert judge_relevance([], [_Span("a.py", 1, 10)]) == []


def test_empty_relevant_spans() -> None:
    retrieved = [_Span("a.py", 1, 10)]
    assert judge_relevance(retrieved, []) == [frozenset()]
