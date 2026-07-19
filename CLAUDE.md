# CLAUDE.md — jsk AI TOKEN SAVER

## Project purpose

Reduce visible tokens per correctly completed agent task without weakening correctness, safety, required evidence, exit-code preservation, or success rate.

## Native skill

Claude Code discovers the project skill at:

`.claude/skills/jsk-ai-token-saver/SKILL.md`

For repository, research, long-session, multi-agent, repeated tool/file, or token-saving work, invoke `/jsk-ai-token-saver` and apply its active saving loop before any measurement. Its canonical cross-agent package is `.agents/skills/jsk-ai-token-saver/SKILL.md`.

Optional runtime: `claude --plugin-dir .` loads the compact SessionStart kernel, per-turn reminder, and bounded agents without changing user settings.

## Active saving rules

- Reuse verified current context, then use project pointers, targeted search, and exact line slices.
- Do not reread unchanged files or repeat successful expensive checks without a changed boundary.
- Batch independent lookups; request bounded logs and decisive errors only.
- Subagents return final evidence, paths, verification, risk, and verdict—not intermediate reasoning.
- Evaluators are used only to verify a policy change, A/B comparison, trace problem, or measured claim.
- Keep detailed procedures in the skill; do not duplicate them here.

## Invariants

- Correctness and safety are evaluated before token reduction.
- Never claim provider billing or hidden-reasoning measurement from visible fixture counts.
- Never weaken markers, thresholds, exits, or success gates to force a PASS.
- Public fixtures contain only synthetic, anonymized, or user-approved data.
- Server, security, database, permission, and deployment reports keep all required fields.

## Verify

```bash
uv sync
uv run python -m unittest discover -s tests -v
uv run python scripts/token_ab_benchmark.py benchmarks/internal-report-ab.json --encoding o200k_base
uv run python scripts/token_visible_benchmark.py benchmarks/toon-v2.3.1-uniform-visible.json --encoding o200k_base
uv run python scripts/head_to_head_benchmark.py benchmarks/caveman-head-to-head-v0.4.json --output reports/caveman-head-to-head-v0.4.json --dry-run

# expected-fail exit 1
set +e
uv run python scripts/token_visible_benchmark.py benchmarks/toon-v2.3.1-nested-guard-visible.json --encoding o200k_base
test $? -eq 1
set -e
```
