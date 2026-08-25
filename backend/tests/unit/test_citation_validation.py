"""The citation-validation logic itself (docs/adr/0005's core defense) is
exercised without hitting the Anthropic API by testing the filtering rule
directly: only chunk_ids present in the retrieved set may survive."""


def filter_citations(raw_citations: list[str], retrieved_ids: set[str]) -> tuple[list[str], int]:
    valid = [cid for cid in raw_citations if cid in retrieved_ids]
    return valid, len(raw_citations) - len(valid)


def test_valid_citations_pass_through() -> None:
    retrieved = {"a.py:1-5", "b.py:10-20"}
    valid, rejected = filter_citations(["a.py:1-5"], retrieved)
    assert valid == ["a.py:1-5"]
    assert rejected == 0


def test_hallucinated_citation_is_rejected() -> None:
    retrieved = {"a.py:1-5"}
    valid, rejected = filter_citations(["a.py:1-5", "z.py:999-1000"], retrieved)
    assert valid == ["a.py:1-5"]
    assert rejected == 1


def test_all_citations_hallucinated() -> None:
    retrieved = {"a.py:1-5"}
    valid, rejected = filter_citations(["z.py:1-2", "y.py:3-4"], retrieved)
    assert valid == []
    assert rejected == 2
