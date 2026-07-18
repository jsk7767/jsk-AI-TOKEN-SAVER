#!/usr/bin/env python
"""Measure internal-report A/B fixtures with an exact tokenizer.

The evaluator is dependency-free when called with a token_counter. The CLI uses
`tiktoken` deliberately and fails rather than silently substituting an estimate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable


ALLOWED_MODES = {"clear", "compact", "minimal"}
SAFE_MODES = {"compact", "minimal"}


def _savings_percent(baseline_tokens: int, candidate_tokens: int) -> float:
    if baseline_tokens <= 0:
        return 0.0
    return round((baseline_tokens - candidate_tokens) * 100 / baseline_tokens, 2)


def evaluate_suite(
    suite: dict[str, Any], token_counter: Callable[[str], int]
) -> dict[str, Any]:
    """Evaluate marker retention and exact token reduction for one fixture suite."""
    minimum = float(suite.get("minimum_safe_savings_percent", 0))
    case_results: list[dict[str, Any]] = []
    safe_baseline_tokens = 0
    safe_candidate_tokens = 0
    safe_case_count = 0

    for case in suite.get("cases", []):
        mode = str(case.get("mode", ""))
        baseline = str(case.get("baseline", ""))
        candidate = str(case.get("candidate", ""))
        required_markers = [str(marker) for marker in case.get("required_markers", [])]
        baseline_exit = case.get("baseline_exit")
        candidate_exit = case.get("candidate_exit")
        baseline_tokens = int(token_counter(baseline))
        candidate_tokens = int(token_counter(candidate))
        missing_markers = [marker for marker in required_markers if marker not in candidate]
        failure_reasons: list[str] = []

        if mode not in ALLOWED_MODES:
            failure_reasons.append("unknown_mode")
        if mode in ALLOWED_MODES and not required_markers:
            failure_reasons.append("required_markers_empty")
        if missing_markers:
            failure_reasons.append("missing_required_markers")
        has_baseline_exit = baseline_exit is not None
        has_candidate_exit = candidate_exit is not None
        if has_baseline_exit != has_candidate_exit:
            failure_reasons.append("exit_code_incomplete")
        elif has_baseline_exit and baseline_exit != candidate_exit:
            failure_reasons.append("exit_code_mismatch")
        if mode in SAFE_MODES and candidate_tokens >= baseline_tokens:
            failure_reasons.append("candidate_not_shorter")

        if mode in SAFE_MODES:
            safe_case_count += 1
            safe_baseline_tokens += baseline_tokens
            safe_candidate_tokens += candidate_tokens

        case_results.append(
            {
                "id": str(case.get("id", "")),
                "mode": mode,
                "baseline_tokens": baseline_tokens,
                "candidate_tokens": candidate_tokens,
                "savings_percent": _savings_percent(
                    baseline_tokens, candidate_tokens
                ),
                "baseline_exit": baseline_exit,
                "candidate_exit": candidate_exit,
                "missing_markers": missing_markers,
                "failure_reasons": failure_reasons,
                "pass": not failure_reasons,
            }
        )

    safe_savings_percent = (
        _savings_percent(safe_baseline_tokens, safe_candidate_tokens)
        if safe_case_count
        else None
    )
    threshold_pass = (
        safe_savings_percent is None or safe_savings_percent >= minimum
    )
    all_cases_pass = all(case["pass"] for case in case_results)

    benchmark_scope = str(
        suite.get("benchmark_scope", "representative_internal_report_fixtures")
    )
    try:
        schema_version = int(suite.get("schema_version", 1))
    except (TypeError, ValueError):
        schema_version = -1
    suite_failure_reasons: list[str] = []
    if schema_version != 1:
        suite_failure_reasons.append("unsupported_schema_version")
    if not case_results:
        suite_failure_reasons.append("no_cases")

    return {
        "schema_version": 1,
        "benchmark_scope": benchmark_scope,
        "billing_claim": False,
        "minimum_safe_savings_percent": minimum,
        "safe_case_count": safe_case_count,
        "safe_baseline_tokens": safe_baseline_tokens,
        "safe_candidate_tokens": safe_candidate_tokens,
        "safe_savings_percent": safe_savings_percent,
        "threshold_pass": threshold_pass,
        "all_cases_pass": all_cases_pass,
        "suite_failure_reasons": suite_failure_reasons,
        "pass": not suite_failure_reasons and all_cases_pass and threshold_pass,
        "cases": case_results,
    }


def _tiktoken_counter(encoding_name: str) -> tuple[Callable[[str], int], str]:
    try:
        import tiktoken
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "tiktoken is required for exact measurement. "
            "Run: uv run --with tiktoken python scripts/token_ab_benchmark.py ..."
        ) from exc

    encoding = tiktoken.get_encoding(encoding_name)
    return lambda text: len(encoding.encode(text)), str(tiktoken.__version__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exact-token A/B benchmark for internal agent reports"
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
        result = evaluate_suite(suite, token_counter=counter)
    except (OSError, TypeError, ValueError, RuntimeError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 2

    result["tokenizer"] = {
        "library": "tiktoken",
        "version": tokenizer_version,
        "encoding": args.encoding,
        "exact_for_fixture_text": True,
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
