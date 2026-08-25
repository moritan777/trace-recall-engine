import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trace_recall.composition_stress import composition_stress_markdown, evaluate_composition_stress  # noqa: E402


DATASET = Path(__file__).resolve().parents[1] / "eval_governance" / "composition_stress" / "scenarios.jsonl"
REQUIRED_COVERAGE = {
    "generic-word dominance", "multiple person/name candidates", "direct-match dominance",
    "depth-2 associative target", "multi-thread target", "strong irrelevant competitor",
    "rare-but-valid target", "repeated-but-low-value competitor", "mixed-person preferences",
    "same-person multiple preferences", "rank 1-3 target", "rank 4-6 target",
    "rank 7-10 target", "selected-group-but-word-suppressed",
}


def load_rows():
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line]


class CompositionStressTests(unittest.TestCase):
    def test_dataset_contract_coverage_and_non_legacy_ratio(self):
        rows = load_rows()
        self.assertGreaterEqual(len(rows), 25)
        self.assertLessEqual(len(rows), 40)
        coverage = {tag for row in rows for tag in row["annotation"]["coverage_tags"]}
        self.assertLessEqual(REQUIRED_COVERAGE - coverage, {"rank 1-3 target", "rank 4-6 target", "rank 7-10 target"})
        self.assertTrue({"rank_1_3", "rank_4_6", "rank_7_10"} <= coverage)
        legacy = sum("legacy_turn_11_or_97_shape" in row["annotation"]["coverage_tags"] for row in rows)
        self.assertGreaterEqual((len(rows) - legacy) / len(rows), .8)
        for row in rows:
            annotation = row["annotation"]
            self.assertEqual(annotation["responsibility"], "ASSOCIATIVE_RECALL_EXPECTED")
            self.assertIn(annotation["expectation"], {"SHOULD_RECALL", "SHOULD_NOT_RECALL"})
            self.assertIsInstance(annotation["expected_internal_recall"], bool)
            self.assertIsInstance(annotation["expected_external_mention"], bool)
            self.assertNotIn("STABLE_FACT", json.dumps(row))
        by_condition = {row["composition_features"]["primary_condition"]: row for row in rows}
        depth = by_condition["depth-2 associative target"]
        self.assertEqual(next(group for group in depth["candidate_groups"] if depth["annotation"]["expected_target"] in group["words"])["activation_depth"], 2)
        rare = by_condition["rare-but-valid target"]
        self.assertEqual(next(group for group in rare["candidate_groups"] if rare["annotation"]["expected_target"] in group["words"])["frequency"], 1)
        repeated = by_condition["repeated-but-low-value competitor"]
        self.assertTrue(any(group.get("low_value_competitor") and group.get("occurrence_count", 0) > 1 for group in repeated["candidate_groups"]))
        mixed = {group.get("preference_owner") for group in by_condition["mixed-person preferences"]["candidate_groups"] if group.get("preference_owner")}
        same = [group.get("preference_owner") for group in by_condition["same-person multiple preferences"]["candidate_groups"] if group.get("preference_owner")]
        self.assertGreater(len(mixed), 1)
        self.assertEqual(len(set(same)), 1)

    def test_all_strategies_emit_required_metrics_and_tradeoffs(self):
        result = evaluate_composition_stress(load_rows())
        self.assertEqual(result["scenario_count"], 30)
        self.assertGreaterEqual(result["non_legacy_shape_rate"], .8)
        self.assertEqual(set(result["strategy_summary"]), {"BASELINE", "DIRECT_MATCH_CAP", "GROUP_DIVERSITY", "GENERIC_WORD_DOWNWEIGHT"})
        required = {"associative_target_recovery", "should_not_recall_leakage", "unexpected_recall", "group_inclusion_rate", "pre_fatigue_admission_rate", "final_working_memory_recall_rate", "selected_group_count", "working_memory_size", "counterexample_count"}
        for strategy, metrics in result["strategy_summary"].items():
            self.assertFalse(required - metrics.keys(), strategy)
            self.assertEqual(len(result["scenario_results"][strategy]), 30)
            self.assertIn("recovery_improved_with_tradeoff", result["tradeoffs"][strategy])
        self.assertGreater(result["tradeoffs"]["GROUP_DIVERSITY"]["new_counterexample_count"], 0)
        self.assertTrue(result["tradeoffs"]["GROUP_DIVERSITY"]["recovery_improved_with_tradeoff"])
        self.assertEqual(result["classifications"]["BASELINE"], "KEEP_BASELINE")
        self.assertEqual(result["classifications"]["GENERIC_WORD_DOWNWEIGHT"], "KEEP_BASELINE")
        self.assertEqual(result["classifications"]["GROUP_DIVERSITY"], "REJECT")
        changed = result["changed_scenarios"]["GROUP_DIVERSITY"]
        self.assertTrue(any("IMPROVEMENT" in row["assessment"] for row in changed))
        self.assertTrue(any("REGRESSION" in row["assessment"] for row in changed))

    def test_markdown_contains_summary_changed_scenarios_and_extracts(self):
        report = composition_stress_markdown(evaluate_composition_stress(load_rows()))
        for heading in ("Strategy summary", "Changed scenarios versus BASELINE", "Extracted trade-off cases"):
            self.assertIn(heading, report)
        for metric in ("Recovery", "SHOULD_NOT leakage", "Unexpected recall", "Avg selected groups", "Avg WM size", "New counterexamples", "Recovered baseline failures"):
            self.assertIn(metric, report)
        self.assertIn("composition-02", report)
        self.assertIn("Improved but broke another scenario", report)
        self.assertIn("REJECT", report)


if __name__ == "__main__":
    unittest.main()
