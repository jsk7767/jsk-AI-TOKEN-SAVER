---
name: jsk-ai-token-saver
description: Reduce agent context, tool, and handoff tokens safely.
version: 0.3.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [token-saving, context, tools, handoffs, agent-workflows, safety]
---

# jsk AI TOKEN SAVER

## Mission

Actively reduce visible tokens used to complete the current task. Save tokens by loading less irrelevant context, returning less redundant tool output, avoiding repeated reads, compressing agent handoffs, and preventing retries or rework.

Do not optimize for answer length alone. The target is the smallest sufficient evidence envelope that completes the task correctly.

## When to use

Load for repository work, research, long sessions, multi-agent work, repeated tool/file use, context pressure, or any request to save/reduce tokens. Once loaded, apply the operating loop during the task; do not start by benchmarking.

## Safety contract

```text
correctness → safety → required evidence → task success → token reduction
```

- A shorter run that causes a follow-up, hides a failure, or requires rework is a regression.
- Keep server, security, database, permission, and deployment reports in `clear` mode with every required field.
- Preserve exact paths, line numbers, commands, exits, error text, rollback state, and PASS/FAIL evidence when they matter.
- Never treat visible-token counts as provider billing or hidden-reasoning measurements.

## Token-saving execution loop

### 1. Context gate

Use this loading ladder and stop when the task has sufficient evidence:

```text
Hot cache → project pointer → context pack/index → targeted search → exact slices → full source only if required
```

- Reuse verified facts, paths, and results already in the current task.
- Read short project pointers (`AGENTS.md`, `CLAUDE.md`) before detailed manuals.
- Search filenames, symbols, routes, tests, or exact errors before reading files.
- Read the smallest useful line range and expand only across a missing dependency or control-flow boundary.
- Do not reread unchanged sources unless the prior range was incomplete or the source changed.
- Do not scan every file or load every document “just in case.”

### 2. Tool gate

- Batch independent lookups in one parallel request.
- Use targeted search before reads and offset/limit pagination for large sources.
- Bound terminal output to changed files, decisive errors, failing tests, or the needed log window.
- For three or more repetitive calls, use a script/tool loop that reduces results before returning them.
- Do not repeat an expensive successful check unless code, config, dependencies, or the asserted boundary changed.
- Stop gathering when the success contract has enough evidence.

### 3. Instruction gate

- Keep project instruction files as pointers: invariants, routes, verification commands, and relevant skill names.
- Keep detailed reusable procedures in one skill/reference and load them only when relevant.
- Do not copy a long policy into every prompt, worker brief, or context file.

### 4. Delegation gate

Delegate only when isolation or parallelism saves more context than the delegation prompt and return cost.

- Send one bounded goal, exact known paths/evidence, forbidden actions, PASS criteria, and return format.
- Return final findings, not intermediate reasoning, raw browsing narratives, or full tool transcripts.
- Use [templates/compact-handoff.md](templates/compact-handoff.md) for normal handoffs.
- Main agents verify external side effects from a returned path, URL, ID, status, or command result instead of importing a worker's full context.

Default depth:

| Role | Mode | Return |
|---|---|---|
| Investigator | `minimal` | location, symbol, evidence, verdict |
| Worker | `compact` | changed paths, behavior, verification, risk, verdict |
| Reviewer | `minimal` | finding, severity, path:line, requested fix |
| QA | `compact` | commands, observed result, PASS/FAIL |
| Server/security/deploy | `clear` | every protected operational field |

### 5. Response gate

- `clear`: user decisions, incidents, security, DB, permissions, production changes, ambiguous failures.
- `compact`: routine completion and worker/QA handoffs.
- `minimal`: code locations, critic findings, lookups, and status where context is already shared.

State each fact once. Keep evidence that prevents a follow-up; remove narration that does not change the decision or next action.

### 6. Context-pressure gate

At a verified milestone preserve only goal, decisions, changed paths, test evidence, blockers, and next action. Drop duplicate excerpts, successful intermediate output, and obsolete hypotheses. Use runtime compaction when needed (`/compact` where supported; `/compress` in Hermes), then resume from the compact state and source pointers.

Never compact unresolved exact errors, security evidence, migration/deployment state, rollback data, or pending user decisions.

For detailed operating rules, read [references/token-saving-playbook.md](references/token-saving-playbook.md). For protected modes and evaluator contracts, read [references/token-saving-policy.md](references/token-saving-policy.md).

## Measurement is verification, not the workflow

Do not run token benchmarks on every task. Use measurement only when changing the policy, comparing a baseline/candidate, diagnosing repeated reads/retries/headroom, or claiming a savings percentage.

- V1 report A/B: [scripts/token_ab_benchmark.py](scripts/token_ab_benchmark.py) with [templates/report-ab.example.json](templates/report-ab.example.json)
- V2 visible trace: [scripts/token_visible_benchmark.py](scripts/token_visible_benchmark.py) with [templates/visible-trace.example.json](templates/visible-trace.example.json)

Exit meaning: `0` PASS, `1` measured contract failure, `2` runtime/input failure.

## Final report

For normal work, report the result in the selected `clear`, `compact`, or `minimal` mode. Mention token counts only when measurement was actually run. Never claim that this skill intercepted model traffic or directly measured provider billing.
