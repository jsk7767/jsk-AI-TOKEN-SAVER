---
name: jsk-ai-token-saver
description: Measure agent token savings without losing correctness.
version: 0.2.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [tokens, benchmark, context, agent-workflows, safety]
---

# jsk AI TOKEN SAVER

## When to use

Load this skill when the user asks to reduce token usage, shorten agent handoffs, compare a baseline with a candidate, audit repeated tool output, or measure visible context headroom.

Do not load it merely to make every user-facing answer short.

## Safety contract

Apply this order without exception:

```text
correctness → safety → required evidence → success rate → token reduction
```

- Missing evidence, a changed exit code, a lower success rate, or a longer safe-mode candidate is `FAIL`.
- Never combine savings percentages from different fixtures or token surfaces.
- Never describe visible fixture counts as provider billing or hidden-reasoning measurements.
- Use only synthetic, anonymized, or user-approved fixture data.
- Server, security, database, permission, and deployment reports stay `clear`; do not compress required fields.

## Choose the evaluator

### V1 report A/B

Use for a baseline and candidate report, reviewer handoff, or tool output pair.

- Evaluator: [scripts/token_ab_benchmark.py](scripts/token_ab_benchmark.py)
- Runnable example: [templates/report-ab.example.json](templates/report-ab.example.json)
- Required evidence: `mode`, baseline, candidate, one or more markers, and both exit codes when exit behavior matters.

### V2 visible trace

Use for captured system/user/tool/assistant traces with repeated reads, retries, success rates, and context headroom.

- Evaluator: [scripts/token_visible_benchmark.py](scripts/token_visible_benchmark.py)
- Runnable example: [templates/visible-trace.example.json](templates/visible-trace.example.json)
- Required evidence: at least three runs per arm by default, correctness markers, declared success, and visible messages.

Read [references/token-saving-policy.md](references/token-saving-policy.md) when changing schemas, thresholds, or protected report modes.

## Execution workflow

1. Locate the directory containing this `SKILL.md`; call it `<skill-dir>`.
2. Copy the closest example from `<skill-dir>/templates/` to a temporary or project-local JSON file.
3. Replace synthetic text with the baseline, candidate, markers, exits, or trace messages being measured. Do not insert credentials or private production records.
4. Run the matching evaluator with exact `tiktoken` counting:

```bash
uv run --with tiktoken python "<skill-dir>/scripts/token_ab_benchmark.py" <fixture.json> --encoding o200k_base --output <report.json>
uv run --with tiktoken python "<skill-dir>/scripts/token_visible_benchmark.py" <trace.json> --encoding o200k_base --output <report.json>
```

5. Interpret the process exit exactly:
   - `0`: contract and token-efficiency gates passed.
   - `1`: measurement completed but the candidate failed the contract.
   - `2`: input, dependency, or runtime error; do not call this an expected safety failure.
6. Read the generated JSON and report the measured scope, token counts, savings, missing markers, failure reasons, and `PASS` or `FAIL`.

When running inside this repository, prefer the root `scripts/`, `benchmarks/`, and `reports/` paths so CI can reproduce the result.

## Required final report

```text
[상태] measured fixture/trace and scope
[의미] what passed or why it failed
[검증] baseline tokens, candidate tokens, savings, markers, exit
[한계] visible text only; no billing or hidden-reasoning claim
[결론] PASS / FAIL
```

This skill is a measurement and operating-policy package. It does not intercept model traffic or automatically reduce API billing.
