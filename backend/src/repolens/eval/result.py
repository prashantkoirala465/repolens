"""The persisted output of one benchmark run: per-question and aggregate
retrieval metrics, plus the config snapshot (embedding provider/model, k
values) needed for a later `repolens-eval diff` to mean anything."""

import json
from pathlib import Path

from pydantic import BaseModel


class QuestionMetrics(BaseModel):
    precision: dict[int, float]
    recall: dict[int, float]
    ndcg: dict[int, float]
    mrr: float


class QuestionResult(BaseModel):
    question_id: str
    question: str
    retrieved_chunk_ids: list[str]
    metrics: QuestionMetrics


class AggregateMetrics(BaseModel):
    precision: dict[int, float]
    recall: dict[int, float]
    ndcg: dict[int, float]
    mrr: float


class EvalResult(BaseModel):
    label: str
    benchmark_repo_url: str
    benchmark_commit: str
    k_values: list[int]
    embedding_provider: str
    embedding_model: str
    questions: list[QuestionResult]
    aggregate: AggregateMetrics

    def save(self, path: Path) -> None:
        path.write_text(self.model_dump_json(indent=2) + "\n")


def load_result(path: Path) -> EvalResult:
    return EvalResult.model_validate(json.loads(path.read_text()))
