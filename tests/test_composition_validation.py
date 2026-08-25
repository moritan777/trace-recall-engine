import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trace_recall.composition_validation import (  # noqa: E402
    FROZEN_THRESHOLD, validate_composition_signal,
)
from trace_recall.composition_features import extract_preselection_features  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    return [json.loads(line) for line in (ROOT / relative).read_text(encoding="utf-8").splitlines() if line]


def signatures(rows):
    return {
        (tuple(sorted(group["words"])), tuple(sorted(group["member_thread_ids"])))
        for row in rows for group in row["candidate_groups"]
    }


class CompositionValidationTests(unittest.TestCase):
    def test_validation_dataset_is_independent_and_distribution_shifted(self):
        exploration = load("eval_governance/composition_stress/scenarios.jsonl")
        validation = load("eval_governance/composition_validation/scenarios.jsonl")
        self.assertGreaterEqual(len(validation), 40)
        self.assertLessEqual(len(validation), 60)
        self.assertFalse({row["scenario_id"] for row in exploration} & {row["scenario_id"] for row in validation})
        self.assertFalse(signatures(exploration) & signatures(validation))
        self.assertTrue(all(row["generation_metadata"]["outcome_not_consulted"] and row["generation_metadata"]["frozen_threshold_not_consulted"] for row in validation))
        shapes = {row["generation_metadata"]["shape"] for row in validation}
        self.assertEqual(len(shapes), 8)
        self.assertEqual({len(row["candidate_groups"]) for row in validation}, set(range(6, 15)))
        ranks = {tag for row in validation for tag in row["annotation"]["coverage_tags"] if tag.startswith("rank_")}
        self.assertTrue({"rank_1_3", "rank_4_6", "rank_7_10"} <= ranks)
        by_shape = {}
        for row in validation:
            by_shape.setdefault(row["generation_metadata"]["shape"], []).append(extract_preselection_features(row["candidate_groups"], row["group_limit"]))
        avg = lambda shape, feature: sum(item[feature] for item in by_shape[shape]) / len(by_shape[shape])
        self.assertLess(avg("low-generic-high-overlap", "generic_ratio"), avg("high-generic-low-overlap", "generic_ratio"))
        self.assertGreater(avg("low-generic-high-overlap", "mean_group_word_overlap"), avg("high-generic-low-overlap", "mean_group_word_overlap"))
        self.assertGreater(avg("high-source-diversity", "total_unique_source_threads"), avg("low-source-diversity", "total_unique_source_threads"))
        self.assertGreater(avg("flat-score-distribution", "score_entropy"), avg("sharp-score-concentration", "score_entropy"))

    def test_frozen_rule_is_not_retrained_and_output_is_deterministic(self):
        exploration = load("eval_governance/composition_stress/scenarios.jsonl")
        validation = load("eval_governance/composition_validation/scenarios.jsonl")
        first = validate_composition_signal(exploration, validation)
        self.assertEqual(first, validate_composition_signal(exploration, validation))
        frozen = first["frozen_rule_validation"]
        self.assertEqual(frozen["threshold"], FROZEN_THRESHOLD)
        self.assertFalse(frozen["retrained"])
        self.assertEqual(first["validation_dataset"]["scenario_count"], 48)
        self.assertIn(first["generalization_judgement"], {"SIGNAL_DID_NOT_GENERALIZE", "WEAKLY_GENERALIZED", "CONSISTENT_GENERALIZATION"})
        self.assertIn("exploratory only", first["fresh_rule_exploration"]["scope"])


if __name__ == "__main__":
    unittest.main()
