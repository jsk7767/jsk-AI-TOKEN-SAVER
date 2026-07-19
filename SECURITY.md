# Security Policy

## Supported version

Security fixes target the current `main` branch and latest tagged release.

## Runtime boundary

The installable Agent Skill under `.agents/skills/jsk-ai-token-saver/` is documentation plus offline evaluators. It does not install hooks, modify agent settings, persist state, read credentials, or contact a network service.

The optional Claude runtime is defined by `.claude-plugin/plugin.json` and `src/hooks/`:

- SessionStart performs a bounded, read-only load of the local `SKILL.md` body.
- UserPromptSubmit emits a fixed reminder of 40 `o200k_base` tokens or less.
- hook code writes no files and provides no telemetry.
- `JSK_TOKEN_SAVER=off` disables both hook outputs for that process.
- plugin activation is opt-in with `claude --plugin-dir .`; this repository does not rewrite `~/.claude/settings.json`.

The Codex hook in `.codex/hooks.json` emits one fixed local rule. It performs no file or network operation.

## Live benchmark boundary

`scripts/head_to_head_benchmark.py` is a repository development tool, not part of the installable Hermes Skill bundle. It has two explicit external effects when a developer runs it:

1. download the public Caveman activation rule from a commit-pinned URL and reject it unless the pinned SHA-256 matches;
2. launch read-only Claude Code subprocesses with fixed tools, model, effort, permission mode, and per-run budget.

The runner does not load `.env`, cookies, API keys, or customer data. Claude authentication remains owned by the installed Claude Code CLI. Benchmark prompts inspect only this public repository, and generated reports must not contain private paths or secrets.

## Data and reporting

- No telemetry is collected by the Skill or hooks.
- Public fixtures use synthetic or repository-public data.
- Reports may include model outputs and provider-reported usage fields; review them before publication.
- Token reports are relative measurements, not provider billing claims.

## Reporting a vulnerability

Use GitHub Security Advisories for this repository when available. Do not open a public issue containing credentials, private paths, or exploit details. Include the affected path, version/commit, reproduction steps, and impact without attaching secrets.
