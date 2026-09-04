"""Hand-labeled retrieval benchmark: ground-truth answer locations per
question, checked against a repo pinned at a specific commit so the labels
never drift out from under the codebase they describe.
"""

import json
from pathlib import Path

from pydantic import BaseModel, model_validator


class RelevantSpan(BaseModel):
    file_path: str
    start_line: int
    end_line: int


class BenchmarkQuestion(BaseModel):
    id: str
    question: str
    relevant_spans: list[RelevantSpan]

    @model_validator(mode="after")
    def _at_least_one_relevant_span(self) -> "BenchmarkQuestion":
        if not self.relevant_spans:
            raise ValueError(f"question {self.id!r} has no relevant_spans")
        return self


class Benchmark(BaseModel):
    repo_url: str
    commit: str
    questions: list[BenchmarkQuestion]

    @model_validator(mode="after")
    def _unique_question_ids(self) -> "Benchmark":
        ids = [q.id for q in self.questions]
        duplicates = {i for i in ids if ids.count(i) > 1}
        if duplicates:
            raise ValueError(f"duplicate question ids: {sorted(duplicates)}")
        return self


def load_benchmark(path: Path) -> Benchmark:
    return Benchmark.model_validate(json.loads(path.read_text()))
