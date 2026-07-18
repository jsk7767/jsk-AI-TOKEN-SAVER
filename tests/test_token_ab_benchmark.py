import json
import unittest
from pathlib import Path

from scripts.token_ab_benchmark import evaluate_suite


class TokenABBenchmarkTests(unittest.TestCase):
    def test_repository_fixture_covers_all_modes_and_passes_contract(self):
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "benchmarks"
            / "internal-report-ab.json"
        )
        suite = json.loads(fixture_path.read_text(encoding="utf-8"))

        result = evaluate_suite(suite, token_counter=len)

        self.assertTrue(result["pass"])
        self.assertEqual(
            {case["mode"] for case in suite["cases"]},
            {"clear", "compact", "minimal"},
        )
        self.assertGreaterEqual(result["safe_case_count"], 3)

    def test_result_uses_fixture_scope_without_turning_it_into_a_billing_claim(self):
        suite = {
            "benchmark_scope": "rtk_tool_output_pilot",
            "minimum_safe_savings_percent": 0,
            "cases": [
                {
                    "id": "git-status",
                    "mode": "compact",
                    "baseline": "modified: app.py",
                    "candidate": "M app.py",
                    "required_markers": ["app.py"],
                }
            ],
        }

        result = evaluate_suite(suite, token_counter=len)

        self.assertEqual(result["benchmark_scope"], "rtk_tool_output_pilot")
        self.assertFalse(result["billing_claim"])

    def test_safe_case_requires_shorter_candidate_and_all_markers(self):
        suite = {
            "minimum_safe_savings_percent": 20,
            "cases": [
                {
                    "id": "worker",
                    "mode": "compact",
                    "baseline": "변경을 수행했습니다. 파일 app.py를 고쳤습니다. 검증 명령 pytest를 실행했고 통과했습니다.",
                    "candidate": "[변경] app.py\n[검증] pytest PASS\n[판정] DONE",
                    "required_markers": ["app.py", "pytest", "PASS", "[판정]"],
                }
            ],
        }

        result = evaluate_suite(suite, token_counter=len)

        self.assertTrue(result["pass"])
        self.assertEqual(result["safe_case_count"], 1)
        self.assertGreaterEqual(result["safe_savings_percent"], 20)
        self.assertEqual(result["cases"][0]["missing_markers"], [])

    def test_missing_required_marker_fails_even_when_candidate_is_shorter(self):
        suite = {
            "minimum_safe_savings_percent": 1,
            "cases": [
                {
                    "id": "reviewer",
                    "mode": "minimal",
                    "baseline": "검토 결과 app.py 10번째 줄에 높은 위험 문제가 있으며 수정이 필요합니다.",
                    "candidate": "app.py:10 HIGH",
                    "required_markers": ["app.py:10", "HIGH", "CHANGES_REQUESTED"],
                }
            ],
        }

        result = evaluate_suite(suite, token_counter=len)

        self.assertFalse(result["pass"])
        self.assertEqual(result["cases"][0]["missing_markers"], ["CHANGES_REQUESTED"])

    def test_tool_case_fails_when_exit_code_changes(self):
        suite = {
            "benchmark_scope": "tool_output_pilot",
            "minimum_safe_savings_percent": 0,
            "cases": [
                {
                    "id": "failing-test",
                    "mode": "compact",
                    "baseline": "FAILED: expected 1, actual 2",
                    "candidate": "FAILED 1",
                    "baseline_exit": 1,
                    "candidate_exit": 0,
                    "required_markers": ["FAILED"],
                }
            ],
        }

        result = evaluate_suite(suite, token_counter=len)

        self.assertFalse(result["pass"])
        self.assertEqual(
            result["cases"][0]["failure_reasons"], ["exit_code_mismatch"]
        )

    def test_tool_case_fails_when_only_one_exit_code_is_provided(self):
        suite = {
            "benchmark_scope": "tool_output_pilot",
            "minimum_safe_savings_percent": 0,
            "cases": [
                {
                    "id": "incomplete-exit-evidence",
                    "mode": "compact",
                    "baseline": "FAILED: expected 1, actual 2",
                    "candidate": "FAILED 1",
                    "baseline_exit": 1,
                    "required_markers": ["FAILED"],
                }
            ],
        }

        result = evaluate_suite(suite, token_counter=len)

        self.assertFalse(result["pass"])
        self.assertIn(
            "exit_code_incomplete", result["cases"][0]["failure_reasons"]
        )

    def test_allowed_case_requires_at_least_one_marker(self):
        suite = {
            "minimum_safe_savings_percent": 0,
            "cases": [
                {
                    "id": "empty-contract",
                    "mode": "minimal",
                    "baseline": "important failure details",
                    "candidate": "x",
                    "required_markers": [],
                }
            ],
        }

        result = evaluate_suite(suite, token_counter=len)

        self.assertFalse(result["pass"])
        self.assertIn(
            "required_markers_empty", result["cases"][0]["failure_reasons"]
        )

    def test_clear_case_preserves_contract_without_reduction_requirement(self):
        clear_text = (
            "상태: 서비스 장애\n의미: 고객 접근 불가\n조치: 원인 조사만 수행\n"
            "검증: health FAIL\n지금 할 일: 배포 승인 필요\nPASS/FAIL: FAIL"
        )
        suite = {
            "minimum_safe_savings_percent": 99,
            "cases": [
                {
                    "id": "incident",
                    "mode": "clear",
                    "baseline": clear_text,
                    "candidate": clear_text + "\n추가 설명: 안전을 위해 자동 배포하지 않음",
                    "required_markers": ["상태:", "의미:", "조치:", "검증:", "지금 할 일:", "PASS/FAIL:"],
                }
            ],
        }

        result = evaluate_suite(suite, token_counter=len)

        self.assertTrue(result["pass"])
        self.assertEqual(result["safe_case_count"], 0)
        self.assertIsNone(result["safe_savings_percent"])
        self.assertTrue(result["cases"][0]["pass"])

    def test_safe_aggregate_threshold_uses_only_compact_and_minimal_cases(self):
        suite = {
            "minimum_safe_savings_percent": 30,
            "cases": [
                {
                    "id": "compact",
                    "mode": "compact",
                    "baseline": "abcdefghij",
                    "candidate": "abcde",
                    "required_markers": ["a"],
                },
                {
                    "id": "clear",
                    "mode": "clear",
                    "baseline": "x",
                    "candidate": "xxxxxxxxxxxxxxxx",
                    "required_markers": ["x"],
                },
            ],
        }

        result = evaluate_suite(suite, token_counter=len)

        self.assertTrue(result["pass"])
        self.assertEqual(result["safe_baseline_tokens"], 10)
        self.assertEqual(result["safe_candidate_tokens"], 5)
        self.assertEqual(result["safe_savings_percent"], 50.0)

    def test_unknown_mode_fails_contract(self):
        suite = {
            "minimum_safe_savings_percent": 0,
            "cases": [
                {
                    "id": "bad-mode",
                    "mode": "short",
                    "baseline": "abc",
                    "candidate": "a",
                    "required_markers": [],
                }
            ],
        }

        result = evaluate_suite(suite, token_counter=len)

        self.assertFalse(result["pass"])
        self.assertEqual(result["cases"][0]["failure_reasons"], ["unknown_mode"])

    def test_explicit_wrong_schema_version_fails_suite(self):
        suite = {
            "schema_version": 2,
            "minimum_safe_savings_percent": 0,
            "cases": [
                {
                    "id": "wrong-schema",
                    "mode": "compact",
                    "baseline": "important evidence PASS",
                    "candidate": "PASS",
                    "required_markers": ["PASS"],
                }
            ],
        }

        result = evaluate_suite(suite, token_counter=len)

        self.assertFalse(result["pass"])
        self.assertEqual(
            result["suite_failure_reasons"], ["unsupported_schema_version"]
        )

        suite["schema_version"] = None
        malformed_result = evaluate_suite(suite, token_counter=len)
        self.assertFalse(malformed_result["pass"])
        self.assertEqual(
            malformed_result["suite_failure_reasons"],
            ["unsupported_schema_version"],
        )

    def test_empty_suite_fails_with_explicit_reason(self):
        result = evaluate_suite(
            {"schema_version": 1, "cases": []}, token_counter=len
        )

        self.assertFalse(result["pass"])
        self.assertEqual(result["suite_failure_reasons"], ["no_cases"])


if __name__ == "__main__":
    unittest.main()
