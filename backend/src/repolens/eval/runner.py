"""Orchestrates one benchmark run: pinned checkout -> chunk -> embed ->
upsert -> query every benchmark question -> score against ground truth.

Chunking, embedding, and storage are the exact same code paths production
indexing uses (`chunking.walker`, `embeddings.factory`, `retrieval.qdrant_store`,
`retrieval.sparse`) so a run measures the real pipeline, not a stand-in.
Indexing writes under a synthetic `eval:{owner}/{name}@{commit}` id via the
store's existing per-repo scoping, so it can never collide with anything
indexed through the app. `mode` is an explicit parameter here, independent
of the app's configured RETRIEVAL_MODE — the whole point of eval is to
compare two modes side by side without touching global config.

Not unit tested: like services/indexer.py and services/git.shallow_clone,
this is I/O all the way down (network clone, a live embedder, live Qdrant).
It's a dev tool, run by hand — see the README's "Measuring retrieval
quality" section.
"""

from typing import Literal

from repolens.chunking.walker import chunk_file, iter_indexable_files
from repolens.core.config import get_settings
from repolens.core.logging import get_logger
from repolens.embeddings.factory import get_embedder
from repolens.eval.benchmark import Benchmark
from repolens.eval.corpus import checkout_at_commit
from repolens.eval.metrics import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank
from repolens.eval.relevance import judge_relevance
from repolens.eval.result import AggregateMetrics, EvalResult, QuestionMetrics, QuestionResult
from repolens.retrieval.qdrant_store import (
    delete_repo_chunks,
    ensure_collection,
    search,
    upsert_chunks,
)
from repolens.retrieval.sparse import embed_sparse_documents, embed_sparse_query
from repolens.services.git import ParsedRepo, cleanup, parse_github_url

logger = get_logger(__name__)


def _eval_repo_id(parsed: ParsedRepo, commit: str) -> str:
    return f"eval:{parsed.owner}/{parsed.name}@{commit}"


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _aggregate(results: list[QuestionResult], k_values: list[int]) -> AggregateMetrics:
    return AggregateMetrics(
        precision={k: _mean([r.metrics.precision[k] for r in results]) for k in k_values},
        recall={k: _mean([r.metrics.recall[k] for r in results]) for k in k_values},
        ndcg={k: _mean([r.metrics.ndcg[k] for r in results]) for k in k_values},
        mrr=_mean([r.metrics.mrr for r in results]),
    )


def run_benchmark(
    benchmark: Benchmark,
    k_values: list[int],
    label: str,
    mode: Literal["dense", "hybrid"] = "dense",
) -> EvalResult:
    if not k_values:
        raise ValueError("k_values must be non-empty")

    parsed = parse_github_url(benchmark.repo_url)
    checkout = checkout_at_commit(parsed, benchmark.commit)
    try:
        files = iter_indexable_files(checkout)
        chunks = [c for path in files for c in chunk_file(checkout, path)]
        if not chunks:
            raise ValueError(f"no indexable files found in {benchmark.repo_url}@{benchmark.commit}")
        logger.info(
            "eval.chunked",
            repo=benchmark.repo_url,
            file_count=len(files),
            chunk_count=len(chunks),
        )

        embedder = get_embedder()
        ensure_collection(embedder.dimension)
        repo_id = _eval_repo_id(parsed, benchmark.commit)
        delete_repo_chunks(repo_id)  # re-running a benchmark: drop the prior version's chunks first
        chunk_texts = [c.text for c in chunks]
        dense_vectors = embedder.embed_documents(chunk_texts)
        sparse_vectors = embed_sparse_documents(chunk_texts)
        upsert_chunks(repo_id, chunks, dense_vectors, sparse_vectors)

        max_k = max(k_values)
        results: list[QuestionResult] = []
        for question in benchmark.questions:
            dense_query_vector = embedder.embed_query(question.question)
            sparse_query_vector = (
                embed_sparse_query(question.question) if mode == "hybrid" else None
            )
            retrieved = search(
                repo_id,
                dense_query_vector,
                top_k=max_k,
                mode=mode,
                sparse_query_vector=sparse_query_vector,
            )
            matches = judge_relevance(retrieved, question.relevant_spans)
            num_relevant = len(question.relevant_spans)
            metrics = QuestionMetrics(
                precision={k: precision_at_k(matches, k) for k in k_values},
                recall={k: recall_at_k(matches, k, num_relevant) for k in k_values},
                ndcg={k: ndcg_at_k(matches, k, num_relevant) for k in k_values},
                mrr=reciprocal_rank(matches),
            )
            results.append(
                QuestionResult(
                    question_id=question.id,
                    question=question.question,
                    retrieved_chunk_ids=[c.chunk_id for c in retrieved],
                    metrics=metrics,
                )
            )
    finally:
        cleanup(checkout)

    settings = get_settings()
    embedding_model = (
        settings.voyage_model
        if settings.embedding_provider == "voyage"
        else settings.ollama_embedding_model
    )
    logger.info("eval.run_complete", label=label, mode=mode, question_count=len(results))
    return EvalResult(
        label=label,
        benchmark_repo_url=benchmark.repo_url,
        benchmark_commit=benchmark.commit,
        k_values=k_values,
        retrieval_mode=mode,
        embedding_provider=settings.embedding_provider,
        embedding_model=embedding_model,
        questions=results,
        aggregate=_aggregate(results, k_values),
    )
