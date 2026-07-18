#!/usr/bin/env python
"""Measure visible tokens per correctly completed task from captured traces.

This evaluator deliberately counts only text that a trace records as visible to
the model. It does not claim provider billing accuracy or hidden-reasoning usage.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Callable


TokenCounter = Callable[[str], int]


def _distribution(samples: list[int]) -> dict[str, Any]:
    ordered = sorted(samples)
    if not ordered:
        return {"samples": [], "median": None, "p90": None, "mean": None}
    p90_index = max(0, math.ceil(len(ordered) * 0.9) - 1)
    return {
        "samples": ordered,
        "median": statistics.median(ordered),
        "p90": ordered[p90_index],
        "mean": round(statistics.fmean(ordered), 2),
    }


def _evaluate_run(
    run: dict[str, Any],
    *,
    required_markers: list[str],
    context_limit_tokens: int,
    token_counter: TokenCounter,
) -> dict[str, Any]:
    role_tokens: dict[str, int] = {}
    visible_tokens = 0
    tool_output_tokens = 0
    repeat_read_tokens = 0
    retry_tokens = 0
    rendered_parts: list[str] = []

    for message in run.get("messages", []):
        role = str(message.get("role", "unknown"))
        text = str(message.get("text", ""))
        tokens = int(token_counter(text))
        visible_tokens += tokens
        role_tokens[role] = role_tokens.get(role, 0) + tokens
        rendered_parts.append(text)
        if role == "tool":
            tool_output_tokens += tokens
        if message.get("repeat_of") is not None:
            repeat_read_tokens += tokens
        if bool(message.get("retry")):
            retry_tokens += tokens

    rendered = "\n".join(rendered_parts)
    missing_markers = [marker for marker in required_markers if marker not in rendered]
    success = bool(run.get("success")) and not missing_markers
    peak_context_tokens = int(run.get("peak_context_tokens", visible_tokens))
    headroom_tokens = max(context_limit_tokens - peak_context_tokens, 0)

    return {
        "success": success,
        "declared_success": bool(run.get("success")),
        "missing_markers": missing_markers,
        "visible_tokens": visible_tokens,
        "tool_output_tokens": tool_output_tokens,
        "repeat_read_tokens": repeat_read_tokens,
        "retry_tokens": retry_tokens,
        "role_tokens": role_tokens,
        "peak_context_tokens": peak_context_tokens,
        "headroom_tokens": headroom_tokens,
    }


def _summarize_arm(
    runs: list[dict[str, Any]],
    *,
    required_markers: list[str],
    context_limit_tokens: int,
    token_counter: TokenCounter,
) -> dict[str, Any]:
    evaluated_runs = [
        _evaluate_run(
            run,
            required_markers=required_markers,
            context_limit_tokens=context_limit_tokens,
            token_counter=token_counter,
        )
        for run in runs
    ]
    successful_runs = [run for run in evaluated_runs if run["success"]]
    n_runs = len(evaluated_runs)
    n_success = len(successful_runs)

    return {
        "n_runs": n_runs,
        "n_success": n_success,
        "success_rate": n_success / n_runs if n_runs else 0.0,
        "visible_tokens": _distribution(
            [run["visible_tokens"] for run in successful_runs]
        ),
        "tool_output_tokens": _distribution(
            [run["tool_output_tokens"] for run in successful_runs]
        ),
        "repeat_read_tokens": _distribution(
            [run["repeat_read_tokens"] for run in successful_runs]
        ),
        "retry_tokens": _distribution(
            [run["retry_tokens"] for run in successful_runs]
        ),
        "headroom_tokens": _distribution(
            [run["headroom_tokens"] for run in successful_runs]
        ),
        "runs": evaluated_runs,
    }


def _savings_percent(baseline: float, candidate: float) -> float:
    if baseline <= 0:
        return 0.0
    return round((baseline - candidate) * 100 / baseline, 2)


def evaluate_visible_suite(
    suite: dict[str, Any], token_counter: TokenCounter
) -> dict[str, Any]:
    """Evaluate captured baseline/candidate traces with success-first gates."""
    runs_required = int(suite.get("runs_required", 3))
    minimum_success_rate = float(suite.get("minimum_success_rate", 1.0))
    task_results: list[dict[str, Any]] = []

    for task in suite.get("tasks", []):
        context_limit_tokens = int(task.get("context_limit_tokens", 0))
        required_markers = [str(item) for item in task.get("required_markers", [])]
        arms = task.get("arms", {})
        baseline = _summarize_arm(
            list(arms.get("baseline", [])),
            required_markers=required_markers,
            context_limit_tokens=context_limit_tokens,
            token_counter=token_counter,
        )
        candidate = _summarize_arm(
            list(arms.get("candidate", [])),
            required_markers=required_markers,
            context_limit_tokens=context_limit_tokens,
            token_counter=token_counter,
        )
        failure_reasons: list[str] = []

        if not required_markers:
            failure_reasons.append("required_markers_empty")
        if baseline["n_runs"] < runs_required:
            failure_reasons.append("baseline_runs_below_required")
        if candidate["n_runs"] < runs_required:
            failure_reasons.append("candidate_runs_below_required")
        if baseline["success_rate"] < minimum_success_rate:
            failure_reasons.append("baseline_success_rate_below_minimum")
        if candidate["success_rate"] < minimum_success_rate:
            failure_reasons.append("candidate_success_rate_below_minimum")
        if candidate["success_rate"] < baseline["success_rate"]:
            failure_reasons.append("candidate_success_rate_regressed")

        baseline_median = baseline["visible_tokens"]["median"]
        candidate_median = candidate["visible_tokens"]["median"]
        savings_percent = None
        if baseline_median is None or candidate_median is None:
            failure_reasons.append("successful_token_sample_missing")
        else:
            savings_percent = _savings_percent(
                float(baseline_median), float(candidate_median)
            )
            if candidate_median >= baseline_median:
                failure_reasons.append("candidate_not_more_token_efficient")

        task_results.append(
            {
                "id": str(task.get("id", "")),
                "context_limit_tokens": context_limit_tokens,
                "required_markers": required_markers,
                "arms": {"baseline": baseline, "candidate": candidate},
                "savings_percent_median": savings_percent,
                "failure_reasons": failure_reasons,
                "pass": not failure_reasons,
            }
        )

    try:
        schema_version = int(suite.get("schema_version", 0))
    except (TypeError, ValueError):
        schema_version = -1
    suite_failures: list[str] = []
    if schema_version != 2:
        suite_failures.append("unsupported_schema_version")
    if not task_results:
        suite_failures.append("no_tasks")

    return {
        "schema_version": 2,
        "benchmark_scope": str(
            suite.get("benchmark_scope", "captured_visible_task_traces")
        ),
        "metric": "visible_tokens_per_correct_task",
        "billing_claim": False,
        "hidden_reasoning_measured": False,
        "runs_required": runs_required,
        "minimum_success_rate": minimum_success_rate,
        "suite_failure_reasons": suite_failures,
        "tasks": task_results,
        "pass": not suite_failures and bool(task_results) and all(
            task["pass"] for task in task_results
        ),
    }


def _tiktoken_counter(encoding_name: str) -> tuple[TokenCounter, str]:
    try:
        import tiktoken
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "tiktoken is required for exact measurement. "
            "Run with: uv run --with tiktoken python scripts/token_visible_benchmark.py ..."
        ) from exc
    encoding = tiktoken.get_encoding(encoding_name)
    return lambda text: len(encoding.encode(text)), str(tiktoken.__version__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exact visible-token benchmark for captured task traces"
    )
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--encoding", default="o200k_base")
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        suite = json.loads(args.fixture.read_text(encoding="utf-8"))
        counter, tokenizer_version = _tiktoken_counter(args.encoding)
        result = evaluate_visible_suite(suite, token_counter=counter)
    except (OSError, TypeError, ValueError, RuntimeError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 2

    result["tokenizer"] = {
        "library": "tiktoken",
        "version": tokenizer_version,
        "encoding": args.encoding,
        "exact_for_visible_trace_text": True,
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
