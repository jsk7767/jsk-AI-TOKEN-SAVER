# Token-Saving Operating Policy

## 1. Purpose

Token saving is not the same as making every response short. The objective is to reduce **visible tokens per correctly completed task** while preserving correctness, safety, and evidence.

Priority order:

```text
correctness → safety → required evidence → task success → token reduction
```

A shorter output that causes a follow-up question, hides a failure, or forces rework is a regression.

## 2. Active saving behavior

The skill reduces tokens during the task before any benchmark is considered.

Required runtime behavior:

- reuse verified current-task context before calling tools
- read project pointers and compact indexes before detailed sources
- search first, then read the smallest useful source slices
- do not reread unchanged sources or rerun unchanged successful checks
- batch independent lookups and bound logs/tool output
- return compact final subagent findings instead of intermediate traces
- select `clear`, `compact`, or `minimal` reporting by risk and recipient
- compact long-session state to goal, decisions, paths, verification, blockers, and next action

The detailed cross-agent procedure is in [`token-saving-playbook.md`](token-saving-playbook.md). Measurement is verification for policy changes and claims; it is not the default task workflow.

## 3. Measurement scope

This project measures only text explicitly present in a fixture or captured trace.

Measured:

- visible system, user, tool, and assistant text
- tool-output, repeated-read, and retry tokens when labeled in a trace
- success rate and required-marker retention
- exact fixture counts using the configured tokenizer

Not measured unless separate telemetry is supplied:

- hidden reasoning
- provider billing
- cache discounts
- all production workloads

Every generated report keeps `billing_claim: false` and, for v2 traces, `hidden_reasoning_measured: false`.

## 4. Report modes

| Mode | Intended use | Reduction requirement |
|---|---|---|
| `clear` | user decisions, incidents, security, database or permission changes | preserve all required fields; shorter output is not required |
| `compact` | worker handoffs and routine QA | candidate must be shorter and preserve markers |
| `minimal` | investigation locations and review findings | candidate must be shorter and preserve markers |

## 5. V1 A/B fixture contract

A v1 fixture uses `schema_version: 1` and a non-empty `cases` array.

Every allowed case must include:

- a supported mode: `clear`, `compact`, or `minimal`
- baseline and candidate text
- at least one `required_markers` entry
- both baseline and candidate exit codes when exit behavior is being checked

Failure conditions include:

- unsupported schema or mode
- empty suite or marker contract
- missing marker
- one-sided or mismatched exit evidence
- a `compact` or `minimal` candidate that is not shorter
- aggregate safe-mode savings below the configured threshold

## 6. V2 visible-trace contract

A v2 fixture uses `schema_version: 2` and a non-empty `tasks` array.

Each task defines:

- a context limit
- at least one correctness marker
- required run count and minimum success rate
- baseline and candidate arms
- visible messages, with optional repeat/retry labels

Only successful runs contribute to token distributions. A candidate fails if its success rate regresses or its successful median is not more token-efficient.

## 7. Expected-fail fixtures

An expected-fail fixture validates that the evaluator rejects an unsafe or inefficient candidate.

- exit `1`: evaluated correctly and failed the contract
- exit `2`: evaluator/runtime error; this is not an expected contract failure

CI must distinguish these exits. Any unexpected pass or runtime error fails CI.

## 8. Public-data rules

Public fixtures must use synthetic or anonymized data only.

Do not include:

- personal paths or user names
- credentials, cookies, tokens, or `.env` values
- real customer or server records
- private tool schemas or internal service inventories

Use documentation-only IP ranges such as `192.0.2.0/24` for security examples.

## 9. Reproduction commands

```bash
uv sync
uv run python -m unittest discover -s tests -v
uv run python scripts/token_ab_benchmark.py \
  benchmarks/internal-report-ab.json \
  --encoding o200k_base \
  --output reports/token-ab-baseline.json
uv run python scripts/token_visible_benchmark.py \
  benchmarks/toon-v2.3.1-uniform-visible.json \
  --encoding o200k_base \
  --output reports/toon-v2.3.1-uniform-visible.json
```

Different token surfaces and candidate percentages must never be added together.
