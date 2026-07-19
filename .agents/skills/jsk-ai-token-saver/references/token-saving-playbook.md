# Active Token-Saving Playbook

## Purpose

Actively reduce visible context, file/tool output, repeated reads, delegation returns, retries, and rework while preserving a correct completed task.

The target is not the shortest answer. The target is the smallest sufficient evidence envelope that lets the agent finish correctly without forcing the user or another agent to ask again.

## 1. Context loading ladder

Use this order and stop as soon as the task has enough evidence:

```text
Hot Cache → Project Pointer → Context Pack / Index → Targeted Search → Exact Slice → Full Source
```

### Hot Cache

Reuse facts, file paths, command results, and decisions already present in the current task. Do not call a tool to rediscover something already verified unless the source changed or the result was incomplete.

### Project Pointer

Read `AGENTS.md`, `CLAUDE.md`, or an equivalent project pointer first. These files should contain invariants and routes, not copied step-by-step manuals. Follow links to a detailed skill only when the current task needs it.

### Context Pack / Index

Prefer a compact code map, task state, index, symbol list, or prior verified handoff over raw documents. For long work, maintain one compact state record containing goal, changed paths, verified commands, decisions, blockers, and the next safe action.

### Targeted Search

Search filenames, symbols, routes, tests, or exact error fragments before opening files. Trace a symbol to its definition and relevant usages instead of reading neighboring directories speculatively.

### Exact Slice

Read the smallest useful line range around a hit. Expand only when an import, caller, schema, or control-flow boundary is missing. Record the path and range mentally or in the task state so unchanged ranges are not read again.

### Full Source

Read a whole source only when its size is small, the task is a full-document review, or targeted slices cannot establish correctness. Full-file reads are a fallback, not the default.

## 2. Tool-output discipline

- Batch independent lookups in one parallel call.
- Use search before read; use line offsets and limits for large files.
- Ask commands for the exact rows needed: changed files, failing tests, recent errors, or bounded log windows.
- Process three or more repetitive lookups with a script/tool loop and return only the reduced result.
- Do not paste full build logs after a clear exit status and decisive error lines are available.
- Do not rerun successful expensive checks unless code, configuration, dependencies, or the asserted boundary changed.
- Stop gathering when the success contract has enough evidence. More context is not automatically safer.

## 3. Knowledge and instruction discipline

- Keep project pointer files short: invariants, routes, verification commands, and skill pointers.
- Store reusable procedures in one skill/reference instead of copying them into every `AGENTS.md`, `CLAUDE.md`, prompt, and subagent brief.
- Load only skills relevant to the current task.
- Never duplicate a long policy into a worker prompt; pass the specific constraints and link/path it needs.

## 4. Delegation discipline

Delegate only when isolation or parallelism saves more context than the delegation prompt and return cost.

A worker brief contains only:

- one bounded goal
- exact paths or evidence already known
- forbidden actions
- PASS criteria
- requested return format

Require workers to return final findings, not intermediate reasoning or raw browsing/tool transcripts. In the repository, use `.agents/skills/jsk-ai-token-saver/templates/compact-handoff.md`; after global installation, use `templates/compact-handoff.md` next to the loaded skill.

Default return depth:

| Role | Mode | Return |
|---|---|---|
| Investigator | `minimal` | location, symbol, evidence, verdict |
| Worker | `compact` | changed paths, behavior, verification, risk, verdict |
| Reviewer | `minimal` | finding, severity, path:line, requested fix |
| QA | `compact` | commands, observed result, PASS/FAIL |
| Server/security/deploy operator | `clear` | all protected operational fields |

Do not retrieve a subagent's full intermediate context into the main conversation. Verify external side effects using the returned file path, URL, ID, status, or command result.

## 5. Response depth

Select one mode before writing:

- `clear`: user decisions, incidents, security, database, permissions, production deployment, and ambiguous failures. Keep every required field.
- `compact`: normal completion and worker/QA handoff. State change, evidence, risk, and verdict once.
- `minimal`: code location, critic finding, lookup result, or status where the recipient already has the task context.

A short answer that causes a follow-up, hides a blocker, or omits a required command/path is a regression.

## 6. Long-session and context-pressure control

At a verified milestone:

1. Preserve only goal, decisions, changed paths, test evidence, blockers, and next action.
2. Drop duplicated source excerpts, successful intermediate outputs, and obsolete hypotheses.
3. Use the runtime's compaction command when pressure is high (`/compact` where supported; `/compress` in Hermes).
4. Resume from the compact state and source pointers instead of replaying the full transcript.

Never compact away exact error text still under investigation, security evidence, deployment/rollback data, database migration state, or unresolved user decisions.

## 7. Verification and measurement

Operational saving is the default. Measurement is occasional verification.

Run the bundled evaluators only when:

- changing this token-saving policy
- comparing a baseline and candidate
- claiming a measured savings percentage
- diagnosing repeated reads, retries, or context headroom

Do not run a benchmark on every ordinary task; benchmark overhead can cost more tokens than it saves.

Required judgment order:

```text
correctness → safety → required evidence → task success → token reduction
```
