import json
import tempfile
import unittest
from pathlib import Path

from scripts.head_to_head_benchmark import (
    _load_source,
    _sanitize_public_value,
    build_claude_command,
    evaluate_head_to_head,
    parse_claude_stream,
    sha256_text,
)


class HeadToHeadBenchmarkTests(unittest.TestCase):
    def test_parse_claude_stream_counts_provider_tokens_tools_and_repeated_reads(self):
        events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "tool-1",
                            "name": "Read",
                            "input": {"file_path": "src/app.py", "offset": 1, "limit": 20},
                        }
                    ]
                },
            },
            {
                "type": "user",
                "message": {
                    "content": [
                        {"type": "tool_result", "tool_use_id": "tool-1", "content": "alpha"}
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "tool-2",
                            "name": "Read",
                            "input": {"file_path": "src/app.py", "offset": 1, "limit": 20},
                        }
                    ]
                },
            },
            {
                "type": "user",
                "message": {
                    "content": [
                        {"type": "tool_result", "tool_use_id": "tool-2", "content": "alpha"}
                    ]
                },
            },
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "num_turns": 2,
                "duration_ms": 1500,
                "total_cost_usd": 0.12,
                "result": "src/app.py:1 alpha",
                "usage": {
                    "input_tokens": 10,
                    "cache_creation_input_tokens": 20,
                    "cache_read_input_tokens": 30,
                    "output_tokens": 40,
                },
                "modelUsage": {"claude-fable-5": {"inputTokens": 10}},
            },
        ]

        parsed = parse_claude_stream(
            "\n".join(json.dumps(event) for event in events), token_counter=len
        )

        self.assertEqual(parsed["provider_total_tokens"], 100)
        self.assertEqual(parsed["tool_calls"], 2)
        self.assertEqual(parsed["repeated_tool_calls"], 1)
        self.assertEqual(parsed["tool_output_visible_tokens"], 10)
        self.assertEqual(parsed["final_text"], "src/app.py:1 alpha")
        self.assertEqual(parsed["num_turns"], 2)
        self.assertFalse(parsed["is_error"])

    def test_build_claude_command_freezes_fair_read_only_controls(self):
        command = build_claude_command(
            prompt="inspect repository",
            model="claude-fable-5",
            append_system_prompt="ARM RULE",
            tools=["Read", "Grep", "Glob"],
            max_budget_usd=0.25,
        )

        rendered = " ".join(command)
        for marker in (
            "--safe-mode",
            "--no-session-persistence",
            "--permission-mode plan",
            "--output-format stream-json",
            "--model claude-fable-5",
            "--effort low",
            "--append-system-prompt ARM RULE",
            "--tools Read,Grep,Glob",
            "--max-budget-usd 0.25",
        ):
            self.assertIn(marker, rendered)

    def test_head_to_head_requires_equal_success_and_lower_jsk_total_tokens(self):
        def run(total, text, tool_calls=1, error=False):
            return {
                "provider_total_tokens": total,
                "final_text": text,
                "tool_calls": tool_calls,
                "repeated_tool_calls": 0,
                "tool_output_visible_tokens": 5,
                "is_error": error,
            }

        suite = {
            "runs_required": 2,
            "minimum_success_rate": 1.0,
            "minimum_task_win_rate": 1.0,
            "prompt_tokens": {"caveman": 163, "jsk": 120},
            "tasks": [
                {
                    "id": "locate",
                    "required_markers": ["src/app.py", "repeat_of"],
                    "minimum_tool_calls": 1,
                    "arms": {
                        "caveman": [
                            run(1200, "src/app.py repeat_of"),
                            run(1100, "src/app.py repeat_of"),
                        ],
                        "jsk": [
                            run(900, "src/app.py repeat_of"),
                            run(950, "src/app.py repeat_of"),
                        ],
                    },
                }
            ],
        }

        result = evaluate_head_to_head(suite)

        self.assertTrue(result["pass"])
        self.assertEqual(result["winner"], "jsk")
        self.assertEqual(result["task_win_rate"], 1.0)
        self.assertGreater(result["aggregate_savings_vs_caveman_percent"], 0)
        self.assertFalse(result["billing_claim"])
        self.assertFalse(result["hidden_reasoning_measured"])

    def test_head_to_head_fails_if_jsk_loses_success_or_token_gate(self):
        suite = {
            "runs_required": 1,
            "minimum_success_rate": 1.0,
            "minimum_task_win_rate": 1.0,
            "prompt_tokens": {"caveman": 100, "jsk": 120},
            "tasks": [
                {
                    "id": "unsafe-shortcut",
                    "required_markers": ["PASS_MARKER"],
                    "minimum_tool_calls": 1,
                    "arms": {
                        "caveman": [
                            {
                                "provider_total_tokens": 1000,
                                "final_text": "PASS_MARKER",
                                "tool_calls": 1,
                                "repeated_tool_calls": 0,
                                "tool_output_visible_tokens": 1,
                                "is_error": False,
                            }
                        ],
                        "jsk": [
                            {
                                "provider_total_tokens": 500,
                                "final_text": "marker omitted",
                                "tool_calls": 0,
                                "repeated_tool_calls": 0,
                                "tool_output_visible_tokens": 0,
                                "is_error": False,
                            }
                        ],
                    },
                }
            ],
        }

        result = evaluate_head_to_head(suite)

        self.assertFalse(result["pass"])
        self.assertEqual(result["winner"], "caveman")
        self.assertIn("jsk_prompt_not_smaller", result["failure_reasons"])
        self.assertIn("jsk_success_rate_below_minimum", result["tasks"][0]["failure_reasons"])

    def test_success_markers_ignore_markdown_backticks_but_not_missing_words(self):
        def run(text):
            return {
                "provider_total_tokens": 100,
                "final_text": text,
                "tool_calls": 1,
                "repeated_tool_calls": 0,
                "tool_output_visible_tokens": 1,
                "is_error": False,
            }

        suite = {
            "runs_required": 1,
            "minimum_success_rate": 1.0,
            "minimum_task_win_rate": 1.0,
            "prompt_tokens": {"caveman": 20, "jsk": 10},
            "tasks": [
                {
                    "id": "markdown-marker",
                    "required_markers": ["exit code 1"],
                    "minimum_tool_calls": 1,
                    "arms": {
                        "caveman": [run("expected exit code 1")],
                        "jsk": [dict(run("expected exit code `1`"), provider_total_tokens=90)],
                    },
                }
            ],
        }

        self.assertTrue(evaluate_head_to_head(suite)["pass"])

    def test_integer_task_win_gate_accepts_exactly_two_of_three(self):
        def run(tokens):
            return {
                "provider_total_tokens": tokens,
                "final_text": "PASS_MARKER",
                "tool_calls": 1,
                "repeated_tool_calls": 0,
                "tool_output_visible_tokens": 1,
                "is_error": False,
            }

        tasks = []
        for index, jsk_tokens in enumerate((90, 90, 110), start=1):
            tasks.append(
                {
                    "id": f"task-{index}",
                    "required_markers": ["PASS_MARKER"],
                    "minimum_tool_calls": 1,
                    "arms": {"caveman": [run(100)], "jsk": [run(jsk_tokens)]},
                }
            )
        suite = {
            "runs_required": 1,
            "minimum_success_rate": 1.0,
            "minimum_task_wins": 2,
            "prompt_tokens": {"caveman": 20, "jsk": 10},
            "tasks": tasks,
        }

        result = evaluate_head_to_head(suite)

        self.assertTrue(result["pass"])
        self.assertEqual(result["task_wins"], 2)
        self.assertEqual(result["minimum_task_wins"], 2)

    def test_local_source_and_trace_paths_are_public_safe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            source = root / "skills" / "SKILL.md"
            source.parent.mkdir(parents=True)
            source.write_text("PUBLIC-SKILL", encoding="utf-8")

            _, metadata = _load_source({"path": "skills/SKILL.md"}, root)
            sanitized = _sanitize_public_value(
                {
                    "windows_path": str(root / "src" / "app.py"),
                    "posix_path": (root / "tests" / "test_app.py").as_posix(),
                    "nested": [f"read {root / 'README.md'}"],
                },
                root=root,
            )
            serialized = json.dumps(sanitized, ensure_ascii=False)

            self.assertEqual(metadata["origin"], "skills/SKILL.md")
            self.assertNotIn(str(root), serialized)
            self.assertNotIn(root.as_posix(), serialized)
            self.assertIn("./src", serialized.replace("\\", "/"))

    def test_sha256_text_is_stable_for_pinned_competitor_rules(self):
        self.assertEqual(
            sha256_text("caveman\n"),
            "c8b7db7e7d6330497a8bf86e246ea67aa4bbc785856f6c9685eeeae7085ba2cb",
        )


if __name__ == "__main__":
    unittest.main()
