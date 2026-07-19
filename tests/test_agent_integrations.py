import json
import re
import subprocess
import tomllib
import unittest
from pathlib import Path

import tiktoken

from scripts.token_ab_benchmark import evaluate_suite
from scripts.token_visible_benchmark import evaluate_visible_suite


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SKILL = ROOT / ".agents" / "skills" / "jsk-ai-token-saver"


class AgentIntegrationTests(unittest.TestCase):
    def test_canonical_agent_skill_has_required_package_files(self):
        skill_text = (CANONICAL_SKILL / "SKILL.md").read_text(encoding="utf-8")

        self.assertTrue(skill_text.startswith("---\n"))
        self.assertRegex(skill_text, r"(?m)^name: jsk-ai-token-saver$")
        self.assertRegex(skill_text, r"(?m)^description: Reduce .+$")
        skill_version = re.search(r"(?m)^version: (.+)$", skill_text).group(1)
        project = tomllib.loads(
            (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(skill_version, project["project"]["version"])
        self.assertEqual(skill_version, "0.4.0")
        for relative_path in (
            "scripts/token_ab_benchmark.py",
            "scripts/token_visible_benchmark.py",
            "templates/report-ab.example.json",
            "templates/visible-trace.example.json",
            "templates/compact-handoff.md",
            "references/token-saving-policy.md",
            "references/token-saving-playbook.md",
        ):
            self.assertTrue((CANONICAL_SKILL / relative_path).is_file(), relative_path)

        for operating_contract in (
            "JSK-SAVE",
            "cache→search→slice",
            "No unchanged reread",
            "batch independent",
            "findings, not transcripts",
            "Measure only for A/B or claims",
            "Load linked playbook, policy, or handoff template only when needed",
        ):
            self.assertIn(operating_contract, skill_text)

    def test_active_kernel_is_smaller_than_caveman_activation_rule(self):
        skill_text = (CANONICAL_SKILL / "SKILL.md").read_text(encoding="utf-8")
        body = re.sub(r"^---[\s\S]*?---\s*", "", skill_text)
        encoding = tiktoken.get_encoding("o200k_base")

        self.assertLessEqual(len(encoding.encode(body)), 160)
        self.assertLessEqual(len(encoding.encode(skill_text)), 300)

    def test_packaged_evaluators_match_repository_sources(self):
        for filename in (
            "token_ab_benchmark.py",
            "token_visible_benchmark.py",
        ):
            self.assertEqual(
                (ROOT / "scripts" / filename).read_bytes(),
                (CANONICAL_SKILL / "scripts" / filename).read_bytes(),
                filename,
            )
        self.assertEqual(
            (ROOT / "docs" / "token-saving-policy.md").read_bytes(),
            (CANONICAL_SKILL / "references" / "token-saving-policy.md").read_bytes(),
        )
        self.assertEqual(
            (ROOT / "docs" / "token-saving-playbook.md").read_bytes(),
            (CANONICAL_SKILL / "references" / "token-saving-playbook.md").read_bytes(),
        )
        playbook = (ROOT / "docs" / "token-saving-playbook.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("(../templates/compact-handoff.md)", playbook)
        self.assertIn(
            ".agents/skills/jsk-ai-token-saver/templates/compact-handoff.md",
            playbook,
        )

    def test_project_agent_discovery_files_exist_and_claude_adapter_is_safe(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        claude_skill = (
            ROOT / ".claude" / "skills" / "jsk-ai-token-saver" / "SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertIn(".agents/skills/jsk-ai-token-saver/SKILL.md", agents)
        self.assertIn(".claude/skills/jsk-ai-token-saver/SKILL.md", claude)
        self.assertIn(".agents/skills/jsk-ai-token-saver/SKILL.md", claude_skill)
        self.assertIn(
            "correctness → safety → required evidence → task success → token reduction",
            claude_skill,
        )
        self.assertIn("scripts/token_ab_benchmark.py", claude_skill)
        self.assertIn("No unchanged reread", claude_skill)
        self.assertIn("findings, not transcripts", claude_skill)
        self.assertIn("expected-fail exit 1", claude)
        encoding = tiktoken.get_encoding("o200k_base")
        self.assertLessEqual(len(encoding.encode(claude_skill)), 350)

    def test_claude_and_codex_runtime_hooks_emit_the_compact_kernel(self):
        plugin = json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertIn("SessionStart", plugin["hooks"])
        self.assertIn("UserPromptSubmit", plugin["hooks"])

        activated = subprocess.run(
            ["node", str(ROOT / "src" / "hooks" / "jsk-save-activate.js")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        body = re.sub(
            r"^---[\s\S]*?---\s*",
            "",
            (CANONICAL_SKILL / "SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(activated.strip(), body.strip())

        reinforced = subprocess.run(
            ["node", str(ROOT / "src" / "hooks" / "jsk-save-reinforce.js")],
            cwd=ROOT,
            input='{"prompt":"inspect repository"}',
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        reinforcement = json.loads(reinforced)["hookSpecificOutput"][
            "additionalContext"
        ]
        encoding = tiktoken.get_encoding("o200k_base")
        self.assertLessEqual(len(encoding.encode(reinforcement)), 40)
        self.assertIn("no unchanged reread", reinforcement)

        codex_hooks = json.loads(
            (ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8")
        )
        command = codex_hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        self.assertIn("JSK-SAVE", command)
        self.assertIn("search", command)

    def test_compact_agent_presets_exist_with_bounded_outputs(self):
        contracts = {
            "jsk-scout.md": "path:line",
            "jsk-worker.md": "verified:",
            "jsk-reviewer.md": "severity",
        }
        for filename, marker in contracts.items():
            text = (ROOT / "agents" / filename).read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"))
            self.assertIn(marker, text)
            self.assertIn("Do not return intermediate reasoning", text)

    def test_bundled_skill_avoids_third_party_persistence_directives(self):
        skill_text = (CANONICAL_SKILL / "SKILL.md").read_text(encoding="utf-8")
        playbook = (
            CANONICAL_SKILL / "references" / "token-saving-playbook.md"
        ).read_text(encoding="utf-8")
        bundled_instructions = skill_text + "\n" + playbook

        for forbidden in (
            "Read short project pointers (`AGENTS.md`, `CLAUDE.md`)",
            "Read `AGENTS.md`, `CLAUDE.md`, or an equivalent project pointer",
            "Store reusable procedures in one skill/reference",
        ):
            self.assertNotIn(forbidden, bundled_instructions)
        self.assertIn(
            "Use project constraints already present in the session",
            playbook,
        )
        self.assertIn(
            "Treat one supplied reusable reference as canonical",
            playbook,
        )

    def test_readme_documents_all_three_agent_install_paths(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        hermes_identifier = (
            "jsk7767/jsk-AI-TOKEN-SAVER/.agents/skills/jsk-ai-token-saver"
        )

        for marker in (
            "## Codex · Claude Code · Hermes에서 사용",
            "$HOME/.agents/skills/jsk-ai-token-saver",
            "$HOME/.claude/skills/jsk-ai-token-saver",
            f"hermes skills install '{hermes_identifier}'",
            "## 실제 토큰 절약 방식",
            "측정은 검증 보조",
            "Hot Cache → Pointer → Search → Slice",
        ):
            self.assertIn(marker, readme)
        self.assertNotIn("raw.githubusercontent.com", readme)
        self.assertNotIn("visible-token measurement toolkit", readme)

        report = json.loads(
            (ROOT / "reports" / "token-ab-baseline.json").read_text(encoding="utf-8")
        )
        expected_row = (
            "| Internal report safe modes | "
            f"{report['safe_baseline_tokens']} | {report['safe_candidate_tokens']} | "
            f"{report['safe_savings_percent']}% | PASS |"
        )
        self.assertIn(expected_row, readme)

    def test_caveman_head_to_head_claim_is_success_gated_and_reproducible(self):
        report_text = (
            ROOT / "reports" / "caveman-head-to-head-v0.4.json"
        ).read_text(encoding="utf-8")
        report = json.loads(report_text)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertTrue(report["pass"])
        self.assertEqual(report["winner"], "jsk")
        self.assertEqual(report["task_wins"], 2)
        self.assertEqual(report["minimum_task_wins"], 2)
        self.assertEqual(report["prompt_tokens"], {"caveman": 163, "jsk": 152})
        self.assertEqual(report["aggregate_savings_vs_caveman_percent"], 10.3)
        self.assertFalse(report["billing_claim"])
        self.assertFalse(report["hidden_reasoning_measured"])
        self.assertNotRegex(report_text, r"(?i)[a-z]:[\\/]+users[\\/]+")
        self.assertNotIn(str(Path.home()), report_text)
        self.assertNotIn(Path.home().as_posix(), report_text)
        for task in report["tasks"]:
            self.assertEqual(task["arms"]["caveman"]["success_rate"], 1.0)
            self.assertEqual(task["arms"]["jsk"]["success_rate"], 1.0)

        for marker in (
            "Caveman v1.9.1 head-to-head",
            "10.3%",
            "152",
            "163",
            "3 tasks × 3 trials",
            "reports/caveman-head-to-head-v0.4.json",
            "provider billing claim이 아닙니다",
        ):
            self.assertIn(marker, readme)

    def test_security_document_explains_runtime_and_live_benchmark_boundaries(self):
        security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        for marker in (
            "no telemetry",
            "read-only",
            "pinned SHA-256",
            "head_to_head_benchmark.py",
            "JSK_TOKEN_SAVER=off",
        ):
            self.assertIn(marker, security)

    def test_bundled_examples_pass_their_evaluators(self):
        repository_fixture_text = (
            ROOT / "benchmarks" / "internal-report-ab.json"
        ).read_text(encoding="utf-8")
        self.assertNotRegex(repository_fixture_text, r"\b\d+/\d+\b")

        report_fixture = json.loads(
            (CANONICAL_SKILL / "templates" / "report-ab.example.json").read_text(
                encoding="utf-8"
            )
        )
        visible_fixture = json.loads(
            (
                CANONICAL_SKILL / "templates" / "visible-trace.example.json"
            ).read_text(encoding="utf-8")
        )

        self.assertTrue(evaluate_suite(report_fixture, token_counter=len)["pass"])
        self.assertTrue(
            evaluate_visible_suite(visible_fixture, token_counter=len)["pass"]
        )


if __name__ == "__main__":
    unittest.main()
