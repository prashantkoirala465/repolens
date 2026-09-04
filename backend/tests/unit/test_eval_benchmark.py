import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from repolens.eval.benchmark import Benchmark, load_benchmark

_VALID = {
    "repo_url": "https://github.com/psf/requests",
    "commit": "dae7ef63b4df6eded86637f251fc4e3a06c3b479",
    "questions": [
        {
            "id": "q1",
            "question": "How does X work?",
            "relevant_spans": [
                {"file_path": "a.py", "start_line": 1, "end_line": 10},
            ],
        }
    ],
}


def test_valid_benchmark_parses() -> None:
    benchmark = Benchmark.model_validate(_VALID)
    assert benchmark.repo_url == _VALID["repo_url"]
    assert len(benchmark.questions) == 1
    assert benchmark.questions[0].relevant_spans[0].end_line == 10


def test_question_with_no_relevant_spans_is_rejected() -> None:
    invalid = {**_VALID, "questions": [{"id": "q1", "question": "?", "relevant_spans": []}]}
    with pytest.raises(ValidationError, match="q1"):
        Benchmark.model_validate(invalid)


def test_duplicate_question_ids_are_rejected() -> None:
    question = _VALID["questions"][0]
    invalid = {**_VALID, "questions": [question, question]}
    with pytest.raises(ValidationError, match="duplicate question ids"):
        Benchmark.model_validate(invalid)


def test_missing_required_field_is_rejected() -> None:
    invalid = {"repo_url": "https://github.com/psf/requests", "questions": []}
    with pytest.raises(ValidationError):
        Benchmark.model_validate(invalid)


def test_load_benchmark_reads_json_file(tmp_path: Path) -> None:
    path = tmp_path / "bench.json"
    path.write_text(json.dumps(_VALID))

    benchmark = load_benchmark(path)

    assert benchmark.commit == _VALID["commit"]
    assert benchmark.questions[0].id == "q1"


def test_the_shipped_requests_benchmark_is_valid() -> None:
    path = Path(__file__).parents[2] / "src" / "repolens" / "eval" / "benchmarks" / "requests.json"

    benchmark = load_benchmark(path)

    ids = [q.id for q in benchmark.questions]
    assert len(ids) == len(set(ids))
    assert len(benchmark.questions) >= 10
    assert all(q.relevant_spans for q in benchmark.questions)
