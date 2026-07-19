---
name: jsk-ai-token-saver
description: Reduce agent context, tool, and handoff tokens safely.
version: 0.3.0
---

# Claude Code token-saving adapter

Read and follow the canonical project skill:

[`.agents/skills/jsk-ai-token-saver/SKILL.md`](../../../.agents/skills/jsk-ai-token-saver/SKILL.md)

## Active execution contract

```text
correctness → safety → required evidence → task success → token reduction
```

Apply this during the task before any measurement:

1. Reuse current verified context.
2. Read `CLAUDE.md` as a pointer, then search symbols/errors before files.
3. Read exact line slices; full files are a fallback.
4. Batch independent lookups and bound tool/log output.
5. Do not reread unchanged sources unless the source changed or the prior slice was incomplete.
6. Return final findings, not intermediate reasoning or raw tool transcripts.
7. Use `minimal` for investigation/review, `compact` for worker/QA handoff, and `clear` for server/security/DB/permission/deploy work.
8. Preserve paths, commands, exits, exact unresolved errors, and PASS/FAIL evidence.

Use repository-root `scripts/token_ab_benchmark.py` or `scripts/token_visible_benchmark.py` only when measurement is specifically needed. Measurement verifies a saving policy; it is not the default workflow.

Invoke explicitly with `/jsk-ai-token-saver` or let Claude load it for token-saving, context reduction, repository, research, long-session, or multi-agent tasks.
