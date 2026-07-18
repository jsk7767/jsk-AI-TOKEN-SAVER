# CLAUDE.md — jsk AI TOKEN SAVER

## Project purpose

Reduce visible tokens per correctly completed agent task without weakening correctness, safety, required evidence, exit-code preservation, or success rate.

## Native skill

Claude Code discovers the project skill at:

`.claude/skills/jsk-ai-token-saver/SKILL.md`

For token optimization, report compression, trace measurement, or context-headroom work, invoke `/jsk-ai-token-saver` or load that skill before changing fixtures or evaluators. Its canonical cross-agent package is `.agents/skills/jsk-ai-token-saver/SKILL.md`.

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

# expected-fail exit 1
set +e
uv run python scripts/token_visible_benchmark.py benchmarks/toon-v2.3.1-nested-guard-visible.json --encoding o200k_base
test $? -eq 1
set -e
```
