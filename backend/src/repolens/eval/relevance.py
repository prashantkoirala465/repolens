"""Judges whether a retrieved chunk matches a benchmark question's ground truth.

Ground truth is a set of (file_path, start_line, end_line) spans, not exact
chunk_ids — see eval/benchmark.py for why. A retrieved chunk is relevant to a
question if it falls in the same file and its line range overlaps a labeled
span; it doesn't need to match the span's boundaries exactly.
"""

from collections.abc import Sequence
from typing import Protocol


class Span(Protocol):
    file_path: str
    start_line: int
    end_line: int


def _overlaps(a: Span, b: Span) -> bool:
    return a.file_path == b.file_path and a.start_line <= b.end_line and b.start_line <= a.end_line


def judge_relevance(
    retrieved: Sequence[Span], relevant_spans: Sequence[Span]
) -> list[frozenset[int]]:
    """For each retrieved item, in rank order, the set of relevant_spans
    indices it overlaps (empty if it matches none)."""
    return [
        frozenset(i for i, span in enumerate(relevant_spans) if _overlaps(item, span))
        for item in retrieved
    ]
