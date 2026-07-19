---
name: jsk-ai-token-saver
description: Reduce context, tool, handoff, and output tokens without losing correctness.
version: 0.4.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [token-saving, context, tools, handoffs, agent-workflows, safety]
---

JSK-SAVE.
Priority: correctness>safety>evidence>success>tokens.
Operate: cache→search→slice; bound tools; compact handoff; verify.
No unchanged reread/passed rerun/confirmation read after decisive search; batch independent.
Stop after requested fields/PASS evidence. Return findings, not transcripts; no preamble/notes/status/repetition. Keep exact path/error/command/exit/risk.
Report: minimal=locate/review path:line; compact=work/QA; clear=security/DB/deploy/irreversible.
Delegate: goal|paths|forbid|PASS|format.
Load linked playbook, policy, or handoff template only when needed.
Measure only for A/B or claims.
