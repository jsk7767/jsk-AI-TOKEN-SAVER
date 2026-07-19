import json
import re
import tomllib
import unittest
from pathlib import Path

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
            self.assertIn(relative_path, skill_text)

        for operating_contract in (
            "## Token-saving execution loop",
            "Hot cache → project pointer → context pack/index → targeted search → exact slices",
            "Do not reread unchanged sources",
            "Batch independent lookups",
            "Return final findings, not intermediate reasoning",
            "Measurement is verification, not the workflow",
        ):
            self.assertIn(operating_contract, skill_text)

    def test_packaged_evaluators_match_repository_sources(self):
        for filename in ("token_ab_benchmark.py", "token_visible_benchmark.py"):
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
        self.assertIn("Do not reread unchanged sources", claude_skill)
        self.assertIn("Return final findings, not intermediate reasoning", claude_skill)
        self.assertIn("expected-fail exit 1", claude)

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
