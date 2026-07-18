import unittest

from scripts.token_visible_benchmark import evaluate_visible_suite


class TokenVisibleBenchmarkTests(unittest.TestCase):
    def test_counts_every_visible_role_and_breaks_out_tool_repeat_and_retry_tokens(self):
        suite = {
            "schema_version": 2,
            "benchmark_scope": "synthetic_visible_trace",
            "runs_required": 1,
            "minimum_success_rate": 1.0,
            "tasks": [
                {
                    "id": "all-visible-roles",
                    "context_limit_tokens": 100,
                    "required_markers": ["PASS"],
                    "arms": {
                        "baseline": [
                            {
                                "success": True,
                                "messages": [
                                    {"id": "s1", "role": "system", "text": "SYSTEM"},
                                    {"id": "u1", "role": "user", "text": "USER"},
                                    {"id": "ts1", "role": "tools", "text": "SCHEMA"},
                                    {"id": "t1", "role": "tool", "text": "TOOL"},
                                    {
                                        "id": "t2",
                                        "role": "tool",
                                        "text": "REPEAT",
                                        "repeat_of": "t1",
                                    },
                                    {
                                        "id": "a1",
                                        "role": "assistant",
                                        "text": "RETRY",
                                        "retry": True,
                                    },
                                    {"id": "a2", "role": "assistant", "text": "PASS"},
                                ],
                            }
                        ],
                        "candidate": [
                            {
                                "success": True,
                                "messages": [
                                    {"id": "s1", "role": "system", "text": "S"},
                                    {"id": "u1", "role": "user", "text": "U"},
                                    {"id": "ts1", "role": "tools", "text": "T"},
                                    {"id": "t1", "role": "tool", "text": "O"},
                                    {"id": "a2", "role": "assistant", "text": "PASS"},
                                ],
                                "peak_context_tokens": 8,
                            }
                        ],
                    },
                }
            ],
        }

        result = evaluate_visible_suite(suite, token_counter=len)

        baseline = result["tasks"][0]["arms"]["baseline"]
        candidate = result["tasks"][0]["arms"]["candidate"]
        self.assertEqual(baseline["visible_tokens"]["median"], 35)
        self.assertEqual(baseline["tool_output_tokens"]["median"], 10)
        self.assertEqual(baseline["repeat_read_tokens"]["median"], 6)
        self.assertEqual(baseline["retry_tokens"]["median"], 5)
        self.assertEqual(candidate["headroom_tokens"]["median"], 92)
        self.assertTrue(result["pass"])

    def test_missing_marker_fails_even_when_candidate_is_shorter(self):
        suite = {
            "schema_version": 2,
            "benchmark_scope": "marker_gate",
            "runs_required": 1,
            "minimum_success_rate": 1.0,
            "tasks": [
                {
                    "id": "marker-gate",
                    "context_limit_tokens": 100,
                    "required_markers": ["PASS", "evidence"],
                    "arms": {
                        "baseline": [
                            {
                                "success": True,
                                "messages": [
                                    {"role": "assistant", "text": "PASS evidence complete"}
                                ],
                            }
                        ],
                        "candidate": [
                            {
                                "success": True,
                                "messages": [
                                    {"role": "assistant", "text": "PASS"}
                                ],
                            }
                        ],
                    },
                }
            ],
        }

        result = evaluate_visible_suite(suite, token_counter=len)

        task = result["tasks"][0]
        candidate_run = task["arms"]["candidate"]["runs"][0]
        self.assertFalse(candidate_run["success"])
        self.assertEqual(candidate_run["missing_markers"], ["evidence"])
        self.assertIn("candidate_success_rate_below_minimum", task["failure_reasons"])
        self.assertFalse(result["pass"])

    def test_success_median_excludes_failed_runs_but_success_rate_regression_fails(self):
        suite = {
            "schema_version": 2,
            "benchmark_scope": "success_only_median",
            "runs_required": 3,
            "minimum_success_rate": 0.6,
            "tasks": [
                {
                    "id": "success-only",
                    "context_limit_tokens": 1000,
                    "required_markers": ["OK"],
                    "arms": {
                        "baseline": [
                            {"success": True, "messages": [{"role": "assistant", "text": "OK" * 10}]},
                            {"success": True, "messages": [{"role": "assistant", "text": "OK" * 20}]},
                            {"success": True, "messages": [{"role": "assistant", "text": "OK" * 30}]},
                        ],
                        "candidate": [
                            {"success": True, "messages": [{"role": "assistant", "text": "OK" * 2}]},
                            {"success": False, "messages": [{"role": "assistant", "text": "X"}]},
                            {"success": True, "messages": [{"role": "assistant", "text": "OK" * 4}]},
                        ],
                    },
                }
            ],
        }

        result = evaluate_visible_suite(suite, token_counter=len)

        task = result["tasks"][0]
        candidate = task["arms"]["candidate"]
        self.assertEqual(candidate["visible_tokens"]["samples"], [4, 8])
        self.assertEqual(candidate["visible_tokens"]["median"], 6.0)
        self.assertAlmostEqual(candidate["success_rate"], 2 / 3)
        self.assertIn("candidate_success_rate_regressed", task["failure_reasons"])
        self.assertFalse(task["pass"])

    def test_insufficient_runs_fail_the_task(self):
        suite = {
            "schema_version": 2,
            "runs_required": 3,
            "minimum_success_rate": 1.0,
            "tasks": [
                {
                    "id": "too-few-runs",
                    "context_limit_tokens": 100,
                    "required_markers": [],
                    "arms": {
                        "baseline": [
                            {"success": True, "messages": [{"role": "assistant", "text": "long"}]}
                        ],
                        "candidate": [
                            {"success": True, "messages": [{"role": "assistant", "text": "x"}]}
                        ],
                    },
                }
            ],
        }

        result = evaluate_visible_suite(suite, token_counter=len)

        self.assertIn("baseline_runs_below_required", result["tasks"][0]["failure_reasons"])
        self.assertIn("candidate_runs_below_required", result["tasks"][0]["failure_reasons"])
        self.assertFalse(result["pass"])

    def test_report_never_claims_provider_billing_or_hidden_reasoning(self):
        suite = {
            "schema_version": 2,
            "runs_required": 1,
            "minimum_success_rate": 1.0,
            "tasks": [
                {
                    "id": "honest-scope",
                    "context_limit_tokens": 100,
                    "required_markers": [],
                    "arms": {
                        "baseline": [
                            {"success": True, "messages": [{"role": "assistant", "text": "long"}]}
                        ],
                        "candidate": [
                            {"success": True, "messages": [{"role": "assistant", "text": "x"}]}
                        ],
                    },
                }
            ],
        }

        result = evaluate_visible_suite(suite, token_counter=len)

        self.assertFalse(result["billing_claim"])
        self.assertFalse(result["hidden_reasoning_measured"])
        self.assertEqual(result["metric"], "visible_tokens_per_correct_task")

        for invalid_schema in (1, None):
            with self.subTest(schema_version=invalid_schema):
                suite["schema_version"] = invalid_schema
                invalid_result = evaluate_visible_suite(suite, token_counter=len)
                self.assertFalse(invalid_result["pass"])
                self.assertEqual(
                    invalid_result["suite_failure_reasons"],
                    ["unsupported_schema_version"],
                )

    def test_task_requires_at_least_one_correctness_marker(self):
        suite = {
            "schema_version": 2,
            "runs_required": 1,
            "minimum_success_rate": 1.0,
            "tasks": [
                {
                    "id": "empty-contract",
                    "context_limit_tokens": 100,
                    "required_markers": [],
                    "arms": {
                        "baseline": [
                            {
                                "success": True,
                                "messages": [
                                    {"role": "assistant", "text": "important evidence"}
                                ],
                            }
                        ],
                        "candidate": [
                            {
                                "success": True,
                                "messages": [{"role": "assistant", "text": "x"}],
                            }
                        ],
                    },
                }
            ],
        }

        result = evaluate_visible_suite(suite, token_counter=len)

        self.assertFalse(result["pass"])
        self.assertIn(
            "required_markers_empty", result["tasks"][0]["failure_reasons"]
        )


if __name__ == "__main__":
    unittest.main()
