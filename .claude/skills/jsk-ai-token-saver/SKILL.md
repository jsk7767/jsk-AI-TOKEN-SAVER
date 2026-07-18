---
name: jsk-ai-token-saver
description: Measure agent token savings without losing correctness.
---

# Claude Code adapter

Read and follow the canonical project skill:

[`.agents/skills/jsk-ai-token-saver/SKILL.md`](../../../.agents/skills/jsk-ai-token-saver/SKILL.md)

## Mandatory safety contract

```text
correctness → safety → required evidence → success rate → token reduction
```

- A missing marker, changed exit code, lower success rate, or longer safe-mode candidate is `FAIL`.
- Never present visible fixture counts as API billing or hidden-reasoning measurements.
- Never weaken a fixture contract to force a PASS.
- Keep server, security, database, permission, and deployment reports in `clear` mode with every required field.

## Repository execution

Use the repository-root evaluator paths in this checkout:

```bash
uv run python scripts/token_ab_benchmark.py <fixture.json> --encoding o200k_base --output <report.json>
uv run python scripts/token_visible_benchmark.py <trace.json> --encoding o200k_base --output <report.json>
```

Read the canonical skill before changing schemas, thresholds, protected modes, or report policy. Invoke explicitly with `/jsk-ai-token-saver` or let Claude load it when the user asks to reduce, benchmark, or audit agent token usage.
