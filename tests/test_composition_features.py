import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trace_recall.composition_features import (  # noqa: E402
    analyze_composition_features, extract_preselection_features, threshold_scan,
)


DATASET = Path(__file__).resolve().parents[1] / "eval_governance" / "composition_stress" / "scenarios.jsonl"


def rows():
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line]


class CompositionFeatureTests(unittest.TestCase):
    def test_all_scenarios_extract_target_blind_features(self):
        scenarios = rows()
        result = analyze_composition_features(scenarios)
        self.assertEqual(len(result["feature_table"]), 30)
        forbidden = {"target", "expected", "label", "rank", "scenario", "coverage"}
        for row in result["feature_table"]:
            self.assertFalse(any(any(token in key.lower() for token in forbidden) for key in row["features"]))
        first = scenarios[0]
        before = extract_preselection_features(first["candidate_groups"], first["group_limit"])
        changed = copy.deepcopy(first)
        changed["scenario_id"] = "forbidden-id"
        changed["target_rank"] = 999
        changed["annotation"] = {"expected_target": "different", "expectation": "SHOULD_NOT_RECALL", "coverage_tags": ["different"]}
        after = extract_preselection_features(changed["candidate_groups"], changed["group_limit"])
        self.assertEqual(before, after)

    def test_outcomes_safety_and_output_are_deterministic(self):
        first = analyze_composition_features(rows())
        self.assertEqual(first, analyze_composition_features(rows()))
        self.assertEqual(first["outcome_distribution"], {"RECOVERY": 9, "REGRESSION": 9, "NO_TARGET_CHANGE": 12})
        self.assertEqual(first["recovery_safety_distribution"], {"SAFE_RECOVERY": 7, "RISKY_RECOVERY": 2})

    def test_threshold_and_optional_two_feature_rules_are_bounded(self):
        result = analyze_composition_features(rows())
        self.assertEqual(threshold_scan(result["feature_table"]), threshold_scan(result["feature_table"]))
        self.assertIn("balanced_accuracy", result["best_single_feature_rule"])
        if result["best_two_feature_rule"]:
            self.assertLessEqual(len(result["best_two_feature_rule"]["conditions"]), 2)
        self.assertIn(result["final_judgement"], {"NO_USEFUL_SEPARATOR", "WEAK_RESEARCH_SIGNAL", "STRONG_RESEARCH_SIGNAL"})


if __name__ == "__main__":
    unittest.main()
