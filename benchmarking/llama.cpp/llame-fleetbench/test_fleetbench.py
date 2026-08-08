"""Regression tests for Fleetbench v2's harness-critical behavior."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

import fleetbench
from fleetbench_core import (
    CALIBRATED_SUITE_VERSION,
    ContextOverflowFailure,
    InfrastructureFailure,
    RequestTimeoutFailure,
    ResponseParseFailure,
    bootstrap_interval,
    classify_exception,
    classify_scored_result,
    normalize_chat_response,
)


def response(message, **choice_fields):
    choice = {"message": message, "finish_reason": "stop", **choice_fields}
    return normalize_chat_response(
        {"id": "r1", "model": "actual-model", "choices": [choice],
         "usage": {"prompt_tokens": 11, "completion_tokens": 3}},
        requested_max_tokens=64,
        wall_s=1.0,
    )


class ResponseNormalizationTests(unittest.TestCase):
    def test_content_parts_and_reasoning_stay_separate(self):
        got = response({
            "role": "assistant",
            "content": [{"type": "text", "text": "final"}],
            "reasoning_content": "private scratchpad",
        })
        self.assertEqual(got["content"], "final")
        self.assertEqual(got["reasoning_content"], "private scratchpad")
        self.assertNotIn("private scratchpad", got["content"])

    def test_legacy_function_call_is_normalized(self):
        got = response({
            "role": "assistant", "content": None,
            "function_call": {"name": "lookup", "arguments": {"id": 7}},
        })
        self.assertEqual(got["tool_calls"][0]["function"]["name"], "lookup")
        self.assertEqual(json.loads(got["tool_calls"][0]["function"]["arguments"]), {"id": 7})
        self.assertTrue(any("legacy" in item for item in got["tool_call_diagnostics"]))

    def test_choice_level_reasoning_is_diagnostic_only(self):
        got = response({"role": "assistant", "content": "answer"},
                       reasoning_content="separate work")
        self.assertEqual(got["content"], "answer")
        self.assertEqual(got["reasoning_content"], "separate work")

    def test_flattened_tool_call_and_missing_id_are_supported(self):
        got = response({
            "role": "assistant", "content": "",
            "tool_calls": [{"name": "lookup", "arguments": '{"id":7}'}],
        })
        self.assertEqual(got["tool_calls"][0]["id"], "call_0")
        self.assertEqual(got["tool_calls"][0]["function"]["name"], "lookup")

    def test_invalid_chat_envelope_is_parse_error(self):
        with self.assertRaises(ResponseParseFailure):
            normalize_chat_response({"choices": []}, requested_max_tokens=64, wall_s=1)


class ResultStateTests(unittest.TestCase):
    def test_length_finish_is_truncated_not_wrong_answer(self):
        classified = classify_scored_result(0.0, "empty", {
            "finish_reason": "length", "completion_tokens": 64,
            "requested_max_tokens": 64, "content": "", "tool_calls": [],
        })
        self.assertEqual(classified.state, "truncated")
        self.assertFalse(classified.quality_eligible)

    def test_reasoning_only_answer_is_quality_failure_without_leaking_reasoning(self):
        classified = classify_scored_result(0.0, "empty", {
            "finish_reason": "stop", "content": "", "reasoning_content": "work",
            "tool_calls": [], "requested_max_tokens": 64,
        })
        self.assertEqual((classified.state, classified.failure_type),
                         ("fail", "reasoning_only_empty_answer"))

    def test_candidate_execution_timeout_is_a_quality_failure(self):
        classified = classify_scored_result(0.0, "execution timeout", {
            "finish_reason": "stop", "content": "```python\nwhile True: pass\n```",
            "tool_calls": [], "requested_max_tokens": 64,
        })
        self.assertEqual((classified.state, classified.failure_type),
                         ("fail", "candidate_execution_timeout"))
        self.assertTrue(classified.quality_eligible)

    def test_typed_transport_failures_remain_distinct(self):
        cases = [
            (RequestTimeoutFailure("slow"), "timeout"),
            (ContextOverflowFailure("large"), "context_overflow"),
            (InfrastructureFailure("down"), "infra_error"),
            (ResponseParseFailure("shape"), "parse_error"),
        ]
        for error, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(classify_exception(error)[0].state, expected)

    def test_resume_retries_nonquality_states(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runs.csv"
            rows = [
                {"model": "m", "category": "math", "task_id": "good",
                 "result_state": "fail", "detail": "wrong"},
                {"model": "m", "category": "math", "task_id": "retry",
                 "result_state": "parse_error", "detail": "bad envelope"},
            ]
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            done = fleetbench.load_done(path)
            self.assertIn(("m", "math", "good"), done)
            self.assertNotIn(("m", "math", "retry"), done)


class CalibratedSuiteTests(unittest.TestCase):
    def test_manifest_has_declared_resolution_and_stable_frontier(self):
        manifest = fleetbench.profile_task_manifest("calibrated", {})
        self.assertEqual(len(manifest), 75)
        self.assertTrue(all(len(row["definition_hash"]) == 20 for row in manifest))
        self.assertEqual(
            fleetbench.stable_task_set_hash(manifest),
            fleetbench.stable_task_set_hash(fleetbench.profile_task_manifest("calibrated", {})),
        )
        for category in fleetbench.CATEGORY_ORDER:
            rows = [row for row in manifest if row["category"] == category]
            primary = [row for row in rows if row["score_scope"] in {"both", "complete_only"}]
            legacy = [row for row in rows if row["score_scope"] in
                      {"both", "legacy_only", "legacy_core"}]
            frontier = [row for row in rows if row["frontier_member"]]
            self.assertEqual((len(primary), len(legacy), len(frontier)), (8, 5, 3))
        invalid = {row["task_id"] for row in manifest
                   if row["validity"] == "legacy_invalid_replaced"}
        self.assertEqual(invalid, fleetbench.INVALID_LEGACY_TASK_IDS)

    def test_repository_reference_patches_pass_hidden_tests(self):
        for task_id in fleetbench.CALIBRATED_EXTRA_TASK_IDS["coding"]:
            task = next(item for item in fleetbench.CODING_TASKS if item["id"] == task_id)
            score, detail = fleetbench.score_coding(
                task, {"content": json.dumps({"files": task["reference_files"]})}
            )
            self.assertEqual(score, 1.0, f"{task_id}: {detail}")

    def test_parameterized_math_is_reproducible_and_verifiable(self):
        for task_id in fleetbench.CALIBRATED_EXTRA_TASK_IDS["math"]:
            task = next(item for item in fleetbench.MATH_TASKS if item["id"] == task_id)
            first = fleetbench.materialize_math_task(task, 731)
            again = fleetbench.materialize_math_task(task, 731)
            other = fleetbench.materialize_math_task(task, 732)
            self.assertEqual(first, again)
            self.assertNotEqual(first["variant_id"], other["variant_id"])
            score, detail = fleetbench.score_math(
                first, {"content": json.dumps(first["answers"])}
            )
            self.assertEqual(score, 1.0, f"{task_id}: {detail}")

    def test_bootstrap_interval_handles_partial_scores(self):
        lo, hi = bootstrap_interval([0.0, 0.25, 0.75, 1.0], iterations=500, seed=8)
        self.assertLessEqual(lo, 0.5)
        self.assertGreaterEqual(hi, 0.5)
        self.assertEqual(bootstrap_interval([0.7] * 8), (0.7, 0.7))

    def test_summary_is_version_isolated_and_exposes_n_and_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = fleetbench.profile_task_manifest("calibrated", {})
            task_hash = fleetbench.stable_task_set_hash(manifest)
            (root / "task_manifest.json").write_text(json.dumps({
                "suite_version": CALIBRATED_SUITE_VERSION,
                "task_set_hash": task_hash,
                "tasks": manifest,
            }))
            base = {field: "" for field in fleetbench.CSV_FIELDS}
            rows = [
                dict(base, timestamp="2026-01-01T00:00:00+00:00", model="m",
                     suite_version=fleetbench.LEGACY_SUITE_VERSION, category="math",
                     task_id="math_combinatorics_bundle", result_state="fail", score="0"),
                dict(base, timestamp="2026-08-01T00:00:00+00:00", model="m",
                     suite_version=CALIBRATED_SUITE_VERSION, category="math",
                     task_id="math_combinatorics_bundle", score_scope="both",
                     result_state="pass", score="1", wall_s="1"),
                dict(base, timestamp="2026-08-01T00:00:01+00:00", model="m",
                     suite_version=CALIBRATED_SUITE_VERSION, category="math",
                     task_id="math_mod_tower", score_scope="both", result_state="timeout",
                     failure_type="request_timeout", detail="deadline"),
            ]
            for row in rows:
                fleetbench.append_row(root / "runs.csv", row)
            fleetbench.write_summary(root, lambda _: None)
            report = (root / "summary.md").read_text()
            self.assertIn(f"Suite: `{CALIBRATED_SUITE_VERSION}`", report)
            self.assertIn("1 / 72", report)
            self.assertIn("`timeout` `math/math_mod_tower`", report)
            self.assertIn("Version isolation", report)


if __name__ == "__main__":
    unittest.main()
