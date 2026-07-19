#!/usr/bin/env python
"""Run a success-gated Claude Code comparison against pinned Caveman rules.

Metric: provider-reported processed tokens per correctly completed task.
The total includes input, cache creation, cache reads, and output. It is useful
for same-model/same-task comparisons, but is not a provider billing claim.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import statistics
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any, Callable


TokenCounter = Callable[[str], int]
USAGE_FIELDS = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text", item.get("content", ""))))
        return "\n".join(part for part in parts if part)
    if content is None:
        return ""
    return str(content)


def parse_claude_stream(raw: str, token_counter: TokenCounter) -> dict[str, Any]:
    """Reduce Claude stream-json output to auditable task-level measurements."""
    result_event: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] = []
    seen_tool_ids: set[str] = set()
    seen_tool_keys: set[str] = set()
    seen_tool_results: set[str] = set()
    repeated_tool_calls = 0
    tool_output_visible_tokens = 0
    malformed_lines = 0

    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            malformed_lines += 1
            continue

        event_type = event.get("type")
        if event_type == "assistant":
            message = event.get("message", {})
            for block in message.get("content", []):
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                tool_id = str(block.get("id", ""))
                if tool_id and tool_id in seen_tool_ids:
                    continue
                if tool_id:
                    seen_tool_ids.add(tool_id)
                name = str(block.get("name", "unknown"))
                tool_input = block.get("input", {})
                key = json.dumps(
                    {"name": name, "input": tool_input},
                    sort_keys=True,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                repeated = key in seen_tool_keys
                if repeated:
                    repeated_tool_calls += 1
                else:
                    seen_tool_keys.add(key)
                tool_calls.append(
                    {
                        "id": tool_id,
                        "name": name,
                        "input": tool_input,
                        "repeated": repeated,
                    }
                )
        elif event_type == "user":
            message = event.get("message", {})
            for block in message.get("content", []):
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                tool_id = str(block.get("tool_use_id", ""))
                if tool_id and tool_id in seen_tool_results:
                    continue
                if tool_id:
                    seen_tool_results.add(tool_id)
                tool_output_visible_tokens += int(
                    token_counter(_content_text(block.get("content", "")))
                )
        elif event_type == "result":
            result_event = event

    if result_event is None:
        return {
            "provider_total_tokens": 0,
            "usage": {field: 0 for field in USAGE_FIELDS},
            "tool_calls": len(tool_calls),
            "tool_trace": tool_calls,
            "repeated_tool_calls": repeated_tool_calls,
            "tool_output_visible_tokens": tool_output_visible_tokens,
            "final_text": "",
            "num_turns": 0,
            "duration_ms": 0,
            "total_cost_usd": 0.0,
            "models": [],
            "is_error": True,
            "error": "missing_result_event",
            "malformed_lines": malformed_lines,
        }

    raw_usage = result_event.get("usage", {})
    usage = {field: int(raw_usage.get(field, 0) or 0) for field in USAGE_FIELDS}
    return {
        "provider_total_tokens": sum(usage.values()),
        "usage": usage,
        "tool_calls": len(tool_calls),
        "tool_trace": tool_calls,
        "repeated_tool_calls": repeated_tool_calls,
        "tool_output_visible_tokens": tool_output_visible_tokens,
        "final_text": str(result_event.get("result", "")),
        "num_turns": int(result_event.get("num_turns", 0) or 0),
        "duration_ms": int(result_event.get("duration_ms", 0) or 0),
        "total_cost_usd": float(result_event.get("total_cost_usd", 0.0) or 0.0),
        "models": sorted(str(name) for name in result_event.get("modelUsage", {})),
        "is_error": bool(result_event.get("is_error"))
        or result_event.get("subtype") != "success",
        "error": result_event.get("api_error_status"),
        "malformed_lines": malformed_lines,
    }


def build_claude_command(
    *,
    prompt: str,
    model: str,
    append_system_prompt: str,
    tools: list[str],
    max_budget_usd: float,
) -> list[str]:
    command = [
        "claude",
        "-p",
        "--safe-mode",
        "--no-session-persistence",
        "--permission-mode",
        "plan",
        "--output-format",
        "stream-json",
        "--verbose",
        "--effort",
        "low",
        "--model",
        model,
        "--tools",
        ",".join(tools),
        "--max-budget-usd",
        str(max_budget_usd),
    ]
    if append_system_prompt:
        command.extend(["--append-system-prompt", append_system_prompt])
    command.append(prompt)
    return command


def _median(values: list[int]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))


def _evaluate_run(run: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    text = str(run.get("final_text", ""))
    normalized_text = text.replace("`", "")
    missing = [
        str(marker)
        for marker in task.get("required_markers", [])
        if str(marker).replace("`", "") not in normalized_text
    ]
    forbidden = [
        str(marker)
        for marker in task.get("forbidden_markers", [])
        if str(marker).replace("`", "") in normalized_text
    ]
    minimum_tool_calls = int(task.get("minimum_tool_calls", 0))
    success = (
        not bool(run.get("is_error"))
        and not missing
        and not forbidden
        and int(run.get("tool_calls", 0)) >= minimum_tool_calls
    )
    evaluated = dict(run)
    evaluated.update(
        {
            "success": success,
            "missing_markers": missing,
            "present_forbidden_markers": forbidden,
            "minimum_tool_calls": minimum_tool_calls,
        }
    )
    return evaluated


def _summarize_arm(runs: list[dict[str, Any]], task: dict[str, Any]) -> dict[str, Any]:
    evaluated = [_evaluate_run(run, task) for run in runs]
    successful = [run for run in evaluated if run["success"]]
    n_runs = len(evaluated)
    return {
        "n_runs": n_runs,
        "n_success": len(successful),
        "success_rate": len(successful) / n_runs if n_runs else 0.0,
        "provider_total_tokens_median": _median(
            [int(run["provider_total_tokens"]) for run in successful]
        ),
        "tool_output_visible_tokens_median": _median(
            [int(run.get("tool_output_visible_tokens", 0)) for run in successful]
        ),
        "repeated_tool_calls_total": sum(
            int(run.get("repeated_tool_calls", 0)) for run in successful
        ),
        "runs": evaluated,
    }


def _savings_percent(baseline: float, candidate: float) -> float:
    if baseline <= 0:
        return 0.0
    return round((baseline - candidate) * 100 / baseline, 2)


def evaluate_head_to_head(suite: dict[str, Any]) -> dict[str, Any]:
    """Compare jsk to Caveman without allowing shorter failed runs to win."""
    runs_required = int(suite.get("runs_required", 3))
    minimum_success_rate = float(suite.get("minimum_success_rate", 1.0))
    minimum_task_win_rate = float(suite.get("minimum_task_win_rate", 0.67))
    raw_minimum_task_wins = suite.get("minimum_task_wins")
    minimum_task_wins = (
        int(raw_minimum_task_wins) if raw_minimum_task_wins is not None else None
    )
    prompt_tokens = suite.get("prompt_tokens", {})
    failure_reasons: list[str] = []

    if int(prompt_tokens.get("jsk", 0)) >= int(prompt_tokens.get("caveman", 0)):
        failure_reasons.append("jsk_prompt_not_smaller")

    task_results: list[dict[str, Any]] = []
    task_wins = 0
    comparable_tasks = 0
    caveman_aggregate = 0.0
    jsk_aggregate = 0.0

    for task in suite.get("tasks", []):
        task_failures: list[str] = []
        required_markers = list(task.get("required_markers", []))
        if not required_markers:
            task_failures.append("required_markers_empty")

        arm_results: dict[str, dict[str, Any]] = {}
        for arm_name, runs in task.get("arms", {}).items():
            arm_results[str(arm_name)] = _summarize_arm(list(runs), task)

        caveman = arm_results.get("caveman", _summarize_arm([], task))
        jsk = arm_results.get("jsk", _summarize_arm([], task))
        for arm_name, summary in (("caveman", caveman), ("jsk", jsk)):
            if summary["n_runs"] < runs_required:
                task_failures.append(f"{arm_name}_runs_below_required")
            if summary["success_rate"] < minimum_success_rate:
                task_failures.append(f"{arm_name}_success_rate_below_minimum")
        if jsk["success_rate"] < caveman["success_rate"]:
            task_failures.append("jsk_success_rate_regressed")

        caveman_median = caveman["provider_total_tokens_median"]
        jsk_median = jsk["provider_total_tokens_median"]
        savings = None
        jsk_won = False
        if caveman_median is None or jsk_median is None:
            task_failures.append("successful_token_sample_missing")
        else:
            comparable_tasks += 1
            caveman_aggregate += caveman_median
            jsk_aggregate += jsk_median
            savings = _savings_percent(caveman_median, jsk_median)
            jsk_won = jsk_median < caveman_median
            if jsk_won:
                task_wins += 1

        task_results.append(
            {
                "id": str(task.get("id", "")),
                "required_markers": required_markers,
                "arms": arm_results,
                "jsk_savings_vs_caveman_percent": savings,
                "jsk_won": jsk_won,
                "failure_reasons": task_failures,
                "pass": not task_failures,
            }
        )

    if not task_results:
        failure_reasons.append("no_tasks")
    task_win_rate = task_wins / comparable_tasks if comparable_tasks else 0.0
    if minimum_task_wins is not None and task_wins < minimum_task_wins:
        failure_reasons.append("task_wins_below_minimum")
    elif minimum_task_wins is None and task_win_rate < minimum_task_win_rate:
        failure_reasons.append("task_win_rate_below_minimum")
    if any(
        reason
        for task in task_results
        for reason in task["failure_reasons"]
        if "success" in reason or reason in {"required_markers_empty", "successful_token_sample_missing"}
    ):
        failure_reasons.append("task_success_gate_failed")

    aggregate_savings = None
    if caveman_aggregate > 0:
        aggregate_savings = _savings_percent(caveman_aggregate, jsk_aggregate)
        if jsk_aggregate >= caveman_aggregate:
            failure_reasons.append("aggregate_tokens_not_lower")
    passed = not failure_reasons and all(task["pass"] for task in task_results)

    return {
        "schema_version": 1,
        "metric": "provider_reported_processed_tokens_per_correct_task",
        "billing_claim": False,
        "hidden_reasoning_measured": False,
        "provider_usage_measured": True,
        "runs_required": runs_required,
        "minimum_success_rate": minimum_success_rate,
        "minimum_task_win_rate": minimum_task_win_rate,
        "minimum_task_wins": minimum_task_wins,
        "prompt_tokens": prompt_tokens,
        "task_wins": task_wins,
        "task_win_rate": task_win_rate,
        "aggregate_savings_vs_caveman_percent": aggregate_savings,
        "tasks": task_results,
        "failure_reasons": failure_reasons,
        "winner": "jsk" if passed else "caveman",
        "pass": passed,
    }


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text.strip()
    parts = text.split("---", 2)
    return parts[2].strip() if len(parts) == 3 else text.strip()


def _replace_path_prefix(text: str, path: Path, replacement: str) -> str:
    parts = [part for part in re.split(r"[\\/]+", str(path.resolve())) if part]
    if not parts:
        return text
    pattern = r"[\\/]+".join(re.escape(part) for part in parts)
    pattern += r"(?P<tail>[\\/]+)?"

    def replace(match: re.Match[str]) -> str:
        return f"{replacement}/" if match.group("tail") else replacement

    return re.sub(pattern, replace, text, flags=re.IGNORECASE)


def _sanitize_public_value(value: Any, *, root: Path) -> Any:
    """Replace local repository/home prefixes before a report is published."""
    if isinstance(value, dict):
        return {
            key: _sanitize_public_value(item, root=root)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_public_value(item, root=root) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_public_value(item, root=root) for item in value)
    if not isinstance(value, str):
        return value

    sanitized = _replace_path_prefix(value, root, ".")
    sanitized = _replace_path_prefix(sanitized, Path.home(), "$HOME")
    return sanitized


def _load_source(spec: dict[str, Any], root: Path) -> tuple[str, dict[str, Any]]:
    if "path" in spec:
        source_path = (root / str(spec["path"])).resolve()
        text = source_path.read_text(encoding="utf-8")
        try:
            origin = source_path.relative_to(root.resolve()).as_posix()
        except ValueError:
            origin = f"external/{source_path.name}"
    elif "url" in spec:
        url = str(spec["url"])
        with urllib.request.urlopen(url, timeout=30) as response:
            text = response.read().decode("utf-8")
        origin = url
    else:
        text = str(spec.get("text", ""))
        origin = "inline"

    actual_hash = sha256_text(text)
    expected_hash = str(spec.get("sha256", ""))
    if expected_hash and actual_hash != expected_hash:
        raise ValueError(
            f"source hash mismatch for {origin}: expected {expected_hash}, got {actual_hash}"
        )
    if bool(spec.get("strip_frontmatter")):
        text = _strip_frontmatter(text)
    return text, {"origin": origin, "sha256": actual_hash}


def _token_counter() -> tuple[TokenCounter, str]:
    try:
        import tiktoken
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "tiktoken is required; run with `uv run --with tiktoken python ...`"
        ) from exc
    encoding = tiktoken.get_encoding("o200k_base")
    return lambda text: len(encoding.encode(text)), str(tiktoken.__version__)


def _claude_version() -> str:
    completed = subprocess.run(
        ["claude", "--version"], capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


def run_live_suite(
    config: dict[str, Any],
    *,
    root: Path,
    trials_override: int | None = None,
    selected_arms: list[str] | None = None,
) -> dict[str, Any]:
    counter, tokenizer_version = _token_counter()
    model = str(config["model"])
    tools = [str(tool) for tool in config.get("tools", ["Read", "Grep", "Glob"])]
    max_budget_usd = float(config.get("max_budget_usd", 0.3))
    trials = trials_override or int(config.get("trials", 3))

    prompts: dict[str, str] = {}
    sources: dict[str, Any] = {}
    arm_specs = config.get("arms", {})
    arm_names = selected_arms or list(arm_specs)
    for arm_name in arm_names:
        spec = arm_specs[arm_name]
        if "sources" in spec:
            pieces: list[str] = []
            piece_meta: list[dict[str, Any]] = []
            for source_spec in spec["sources"]:
                text, meta = _load_source(source_spec, root)
                pieces.append(text)
                piece_meta.append(meta)
            prompt = "\n\n".join(pieces)
            source_meta: Any = piece_meta
        elif "source" in spec:
            prompt, source_meta = _load_source(spec["source"], root)
        else:
            prompt = str(spec.get("prompt", ""))
            source_meta = {"origin": "empty", "sha256": sha256_text(prompt)}
        prompts[arm_name] = prompt
        sources[arm_name] = source_meta

    tasks: list[dict[str, Any]] = []
    run_order: list[dict[str, Any]] = []
    for task_index, task_spec in enumerate(config.get("tasks", [])):
        task = {
            "id": str(task_spec["id"]),
            "required_markers": list(task_spec.get("required_markers", [])),
            "forbidden_markers": list(task_spec.get("forbidden_markers", [])),
            "minimum_tool_calls": int(task_spec.get("minimum_tool_calls", 1)),
            "arms": {arm_name: [] for arm_name in arm_names},
        }
        for trial in range(trials):
            rotation = (task_index + trial) % len(arm_names)
            ordered_arms = arm_names[rotation:] + arm_names[:rotation]
            for arm_name in ordered_arms:
                command = build_claude_command(
                    prompt=str(task_spec["prompt"]),
                    model=model,
                    append_system_prompt=prompts[arm_name],
                    tools=tools,
                    max_budget_usd=max_budget_usd,
                )
                completed = subprocess.run(
                    command,
                    cwd=root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=int(config.get("timeout_seconds", 180)),
                )
                parsed = parse_claude_stream(completed.stdout, token_counter=counter)
                parsed["process_exit_code"] = completed.returncode
                if completed.stderr.strip():
                    parsed["stderr"] = completed.stderr.strip()[-2000:]
                if completed.returncode != 0:
                    parsed["is_error"] = True
                task["arms"][arm_name].append(parsed)
                run_order.append(
                    {
                        "task": task["id"],
                        "trial": trial + 1,
                        "arm": arm_name,
                    }
                )
        tasks.append(task)

    suite = {
        "runs_required": trials,
        "minimum_success_rate": float(config.get("minimum_success_rate", 1.0)),
        "minimum_task_win_rate": float(config.get("minimum_task_win_rate", 0.67)),
        "minimum_task_wins": config.get("minimum_task_wins"),
        "prompt_tokens": {name: counter(prompt) for name, prompt in prompts.items()},
        "tasks": tasks,
    }
    result = evaluate_head_to_head(suite)
    result["metadata"] = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "claude_cli_version": _claude_version(),
        "requested_model": model,
        "tools": tools,
        "tokenizer": {
            "library": "tiktoken",
            "version": tokenizer_version,
            "encoding": "o200k_base",
            "prompt_count_exact_for_encoding": True,
        },
        "sources": sources,
        "run_order": run_order,
        "comparison_scope": "same Claude Code model, repository, tools, tasks, effort, and safety controls",
    }
    result["metadata"]["public_path_sanitized"] = True
    return _sanitize_public_value(result, root=root)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trials", type=int)
    parser.add_argument("--arms", help="comma-separated arm names")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        config_path = args.config.resolve()
        config = json.loads(config_path.read_text(encoding="utf-8"))
        root = config_path.parents[1]
        arms = args.arms.split(",") if args.arms else None
        if args.dry_run:
            print(
                json.dumps(
                    {
                        "model": config.get("model"),
                        "trials": args.trials or config.get("trials"),
                        "arms": arms or list(config.get("arms", {})),
                        "tasks": [task.get("id") for task in config.get("tasks", [])],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        result = run_live_suite(
            config,
            root=root,
            trials_override=args.trials,
            selected_arms=arms,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except (KeyError, OSError, RuntimeError, TypeError, ValueError, subprocess.SubprocessError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "pass": result["pass"],
                "winner": result["winner"],
                "task_win_rate": result["task_win_rate"],
                "aggregate_savings_vs_caveman_percent": result[
                    "aggregate_savings_vs_caveman_percent"
                ],
                "prompt_tokens": result["prompt_tokens"],
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
