import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trace_recall.long_horizon import (  # noqa: E402
    compare_long_horizon, select_annotation_turns, summarize_long_horizon,
)


def record(turn=1, selected=True, fatigue=False):
    events = [
        {"stage": "RAW_ACTIVATION", "identifier": "topic", "accepted": True, "reason": "raw activation candidate", "raw_frequency": turn},
        {"stage": "ACTIVATION_GATE", "identifier": "topic", "accepted": selected, "reason": "recently_exposed" if fatigue else "selected", "fatigue_contribution": -3 if fatigue else 0},
        {"stage": "WORKING_MEMORY", "identifier": "topic", "accepted": selected, "reason": "included" if selected else "suppressed"},
    ]
    return {
        "schema_version": 2, "turn": turn,
        "recall": {"activated_words": ["topic", "memory"], "selected_words": ["topic"] if selected else [], "topic_reentry_words": ["topic"] if selected else [], "fatigue_suppressed_words": [{"word": "topic", "suppressed_by_fatigue": True}] if fatigue else [], "stage_diagnostics": events, "activation_analysis": {"candidates": [{"best_depth": 2}], "paths": [{"to_id": "topic"}, {"to_id": "other"}]}},
        "working_memory": {"word_count": int(selected), "thread_group_count": int(selected)},
        "evaluation": {"unexpected_hit_count": 0, "precision_like": 1.0 if selected else 0.0},
        "prompt": {"rough_tokens": 10}, "timing": {"total_ms": float(turn)},
        "governance_observation_config": {"fatigue_threshold": 3},
    }


class LongHorizonTests(unittest.TestCase):
    def test_summary_includes_db_scale_diffusion_frequency_and_fatigue(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "memory.db"
            with sqlite3.connect(db) as connection:
                connection.executescript("CREATE TABLE words(x); CREATE TABLE threads(x); CREATE TABLE word_threads(x); INSERT INTO words VALUES(1); INSERT INTO threads VALUES(1); INSERT INTO word_threads VALUES(1);")
            result = summarize_long_horizon([record(1), record(2, False, True)], db)
        self.assertEqual(result["word_node_count"], 1)
        self.assertEqual(result["topic_fatigue_suppressions"], 1)
        self.assertEqual(result["contributing_paths_per_selected_word"], 1.0)
        self.assertEqual(result["mean_raw_frequency"], 1.5)
        self.assertEqual(result["high_frequency_word_admission"][0]["word"], "topic")
        self.assertIsNone(result["pseudo_reentry_false_positive"])

    def test_comparison_retains_raw_relative_delta_and_sign_classification(self):
        short = summarize_long_horizon([record(1)])
        long = summarize_long_horizon([record(1), record(2, False)])
        result = compare_long_horizon(short, long)
        precision = result["metric_comparison"]["recall_precision"]
        self.assertEqual(precision["classification"], "DEGRADED")
        self.assertIn("raw_delta", precision)
        self.assertIn("relative_delta", precision)

    def test_annotation_template_is_bounded_and_evaluation_only(self):
        selected = select_annotation_turns([record(turn, selected=turn % 3 != 0, fatigue=turn % 5 == 0) for turn in range(1, 60)], 25)
        self.assertLessEqual(len(selected), 25)
        self.assertTrue(selected)
        self.assertTrue(all(row["benchmark_responsibility"] == "AMBIGUOUS" and row["annotation_status"] == "REVIEW_REQUIRED" for row in selected))


if __name__ == "__main__":
    unittest.main()
