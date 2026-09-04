"""`repolens-eval` — run the retrieval benchmark, and compare two runs.

repolens-eval run --benchmark <path> [--k 5,10] [--mode dense|hybrid] \
    [--label NAME] --out result.json
repolens-eval diff <baseline.json> <candidate.json>
"""

from pathlib import Path
from typing import Literal

import click

from repolens.eval.benchmark import load_benchmark
from repolens.eval.result import EvalResult, load_result
from repolens.eval.runner import run_benchmark


def _parse_k_values(raw: str) -> list[int]:
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    try:
        values = sorted({int(part) for part in parts})
    except ValueError as exc:
        raise click.BadParameter("must be a comma-separated list of positive integers") from exc
    if not values or any(v <= 0 for v in values):
        raise click.BadParameter("must be a comma-separated list of positive integers")
    return values


@click.group()
def cli() -> None:
    """Retrieval eval harness: measure retrieval quality, don't assume it."""


@cli.command("run")
@click.option(
    "--benchmark",
    "benchmark_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option("--k", "k_raw", default="5,10", show_default=True, help="comma-separated cutoffs")
@click.option(
    "--mode",
    type=click.Choice(["dense", "hybrid"]),
    default="dense",
    show_default=True,
    help="retrieval strategy to evaluate — independent of the app's RETRIEVAL_MODE",
)
@click.option(
    "--label",
    default="default",
    show_default=True,
    help="name for this run, e.g. 'dense-ollama-top10'",
)
@click.option("--out", "out_path", required=True, type=click.Path(dir_okay=False, path_type=Path))
def run_cmd(
    benchmark_path: Path, k_raw: str, mode: Literal["dense", "hybrid"], label: str, out_path: Path
) -> None:
    """Index the benchmark's pinned commit and score retrieval against it."""
    k_values = _parse_k_values(k_raw)
    benchmark = load_benchmark(benchmark_path)
    click.echo(
        f"Running {len(benchmark.questions)} questions against "
        f"{benchmark.repo_url}@{benchmark.commit[:12]} (mode={mode}, k={k_values})"
    )
    result = run_benchmark(benchmark, k_values, label, mode)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(out_path)
    click.echo(f"Wrote {out_path}")
    _print_aggregate(result)


def _print_aggregate(result: EvalResult) -> None:
    click.echo(
        f"\n{result.label}  ({result.retrieval_mode}, "
        f"{result.embedding_provider}/{result.embedding_model})"
    )
    click.echo(f"  MRR: {result.aggregate.mrr:.3f}")
    for k in result.k_values:
        click.echo(
            f"  @{k}:  precision={result.aggregate.precision[k]:.3f}  "
            f"recall={result.aggregate.recall[k]:.3f}  ndcg={result.aggregate.ndcg[k]:.3f}"
        )


@cli.command("diff")
@click.argument("baseline_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("candidate_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def diff_cmd(baseline_path: Path, candidate_path: Path) -> None:
    """Compare two eval runs: aggregate deltas, and any per-question regression."""
    baseline = load_result(baseline_path)
    candidate = load_result(candidate_path)
    common_k = sorted(set(baseline.k_values) & set(candidate.k_values))
    if not common_k:
        raise click.ClickException("the two runs share no common k values to compare")

    click.echo(
        f"baseline:  {baseline.label} ({baseline.retrieval_mode}, "
        f"{baseline.embedding_provider}/{baseline.embedding_model})"
    )
    click.echo(
        f"candidate: {candidate.label} ({candidate.retrieval_mode}, "
        f"{candidate.embedding_provider}/{candidate.embedding_model})"
    )
    click.echo()
    header = f"{'metric':<14}{'baseline':>10}{'candidate':>10}{'delta':>10}"
    click.echo(header)
    click.echo("-" * len(header))
    _diff_row("mrr", baseline.aggregate.mrr, candidate.aggregate.mrr)
    for k in common_k:
        _diff_row(
            f"precision@{k}", baseline.aggregate.precision[k], candidate.aggregate.precision[k]
        )
        _diff_row(f"recall@{k}", baseline.aggregate.recall[k], candidate.aggregate.recall[k])
        _diff_row(f"ndcg@{k}", baseline.aggregate.ndcg[k], candidate.aggregate.ndcg[k])

    regressions = _find_regressions(baseline, candidate, common_k)
    if regressions:
        click.echo(f"\n{len(regressions)} question(s) regressed on at least one metric:")
        for line in regressions:
            click.echo(f"  - {line}")
    else:
        click.echo("\nNo per-question regressions.")


def _diff_row(name: str, baseline_value: float, candidate_value: float) -> None:
    delta = candidate_value - baseline_value
    click.echo(f"{name:<14}{baseline_value:>10.3f}{candidate_value:>10.3f}{delta:>+10.3f}")


def _find_regressions(
    baseline: EvalResult, candidate: EvalResult, k_values: list[int]
) -> list[str]:
    baseline_by_id = {q.question_id: q for q in baseline.questions}
    regressions: list[str] = []
    for cq in candidate.questions:
        bq = baseline_by_id.get(cq.question_id)
        if bq is None:
            continue
        if cq.metrics.mrr < bq.metrics.mrr:
            regressions.append(
                f"{cq.question_id}: mrr {bq.metrics.mrr:.3f} -> {cq.metrics.mrr:.3f}"
            )
            continue
        for k in k_values:
            if cq.metrics.recall[k] < bq.metrics.recall[k]:
                regressions.append(
                    f"{cq.question_id}: recall@{k} "
                    f"{bq.metrics.recall[k]:.3f} -> {cq.metrics.recall[k]:.3f}"
                )
                break
    return regressions
