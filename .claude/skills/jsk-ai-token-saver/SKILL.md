---
name: jsk-ai-token-saver
description: Reduce context, tool, handoff, and output tokens without losing correctness.
version: 0.4.0
---

# JSK-SAVE Claude adapter

Canonical: [`.agents/skills/jsk-ai-token-saver/SKILL.md`](../../../.agents/skills/jsk-ai-token-saver/SKILL.md)

Priority: correctness → safety → required evidence → task success → token reduction.
Loop: cache→search→slice→bound tools→compact handoff→verify.
No unchanged reread/passed rerun/confirmation read after decisive search; batch independent.
Stop after requested fields/PASS evidence. Return findings, not transcripts; no preamble/notes/status/repetition. Keep exact path/error/command/exit/risk.
Use minimal for locate/review, compact for work/QA, clear for security/DB/deploy/irreversible.
Measure only for A/B or claims: `scripts/token_ab_benchmark.py`.
