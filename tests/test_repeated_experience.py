import copy
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trace_recall.repeated_experience import (
    _state_equivalence,
    analyze_repeated_experience,
    compare_repeated_experience,
    select_repetition_review_queue,
)


class RepeatedExperienceTests(unittest.TestCase):
    def make_db(self, root: Path) -> Path:
        path = root / "memory.db"
        with sqlite3.connect(path) as db:
            db.executescript("""
            CREATE TABLE threads(thread_id TEXT, date TEXT, source_text TEXT, canonical_key TEXT,
              strength REAL, created_at TEXT, last_seen TEXT, seen_count INTEGER, created_by TEXT);
            CREATE TABLE words(word_id TEXT, word TEXT, strength REAL, weight REAL, seen_count INTEGER,
              first_seen TEXT, last_seen TEXT);
            CREATE TABLE word_threads(word_id TEXT, thread_id TEXT, weight_in_thread REAL, added_at TEXT);
            """)
            db.executemany("INSERT INTO words VALUES(?,?,?,?,?,?,?)", [
                ("w1", "coffee", 2, 1, 8, "a", "z"),
                ("w2", "cafe", 1, 1, 3, "a", "z"),
                ("w3", "tea", 1, 1, 2, "a", "z"),
            ])
            db.executemany("INSERT INTO threads VALUES(?,?,?,?,?,?,?,?,?)", [
                ("t1", "d", "coffee at cafe", "k", 1, "2025-01-01", "2025-01-01", 1, "user"),
                ("t2", "d", "coffee at cafe", "k", 1, "2025-01-02", "2025-01-02", 1, "user"),
                ("t3", "d", "tea", "q", 2, "2025-01-03", "2025-01-04", 2, "user"),
            ])
            db.executemany("INSERT INTO word_threads VALUES(?,?,?,?)", [
                ("w1", "t1", 1, "a"), ("w2", "t1", 1, "a"),
                ("w1", "t2", 1, "b"), ("w2", "t2", 1, "b"),
                ("w3", "t3", 1, "c"),
            ])
        return path

    def records(self):
        return [{
            "turn": turn,
            "recall": {
                "selected_words": ["coffee"],
                "activation_analysis": {
                    "candidates": [{"word": "coffee", "score": .8}, {"word": "tea", "score": .2}],
                    "paths": [
                        {"from_type": "thread", "from_id": "t1", "to_type": "word", "to_id": "coffee"},
                        {"from_type": "thread", "from_id": "t2", "to_type": "word", "to_id": "coffee"},
                        {"from_type": "thread", "from_id": "t3", "to_type": "word", "to_id": "tea"},
                    ],
                },
                "stage_diagnostics": [
                    {"stage": "ACTIVATION_GATE", "identifier": "coffee", "accepted": True},
                    {"stage": "ACTIVATION_GATE", "identifier": "tea", "accepted": False},
                ],
            },
            "evaluation": {"expected_words": ["coffee"], "unexpected_words": []},
        } for turn in range(1, 31)]

    def test_state_equivalence_separates_equal_and_different_state(self):
        equal = {"a": {"created_by": "user"}, "b": {"created_by": "user"}}
        different = {"a": {"created_by": "user"}, "b": {"created_by": "assistant"}}
        self.assertEqual(_state_equivalence(["a", "b"], equal)["classification"], "STRUCTURALLY_AND_STATE_EQUIVALENT")
        self.assertEqual(_state_equivalence(["a", "b"], different)["classification"], "STRUCTURALLY_DUPLICATE_BUT_STATE_DIFFERENT")

    def test_grouping_buckets_state_and_counterfactual_are_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self.make_db(Path(tmp)); records = self.records(); original = copy.deepcopy(records)
            first = analyze_repeated_experience(records, db)
            self.assertEqual(first, analyze_repeated_experience(records, db))
            self.assertEqual(records, original)
            self.assertEqual(first["signature_count"], 2)
            self.assertEqual(first["storage_contribution"]["unique_first_instances"], 2)
            self.assertEqual(first["storage_contribution"]["exact_repeat_instances"], 1)
            self.assertEqual(first["repetition_distribution"]["2"]["thread_count"], 2)
            self.assertEqual(first["storage_contribution"]["exact_repeat_instance_generated_paths"], 30)
            self.assertTrue(first["recall_utility"]["expected_target_contributing_signatures"])
            self.assertIn("gate_selection_rate", first["long_term_availability"]["2-4"])
            self.assertEqual(first["high_fanout_repetition"][0]["repeated_signature_instances"], 1)
            counterfactual = first["offline_first_instance_counterfactual"]
            self.assertEqual(counterfactual["marker"], "OFFLINE_TOPOLOGY_COUNTERFACTUAL")
            self.assertEqual(counterfactual["threads_remaining"], 2)
            self.assertEqual(counterfactual["connections_remaining"], 3)
            self.assertFalse(counterfactual["production_replay"])
            repeated = first["top_repeated_signatures"][0]
            self.assertEqual(repeated["state_equivalence"]["classification"], "STRUCTURALLY_DUPLICATE_BUT_STATE_DIFFERENT")
            self.assertIn("created_at", repeated["state_equivalence"]["differing_fields"])
            self.assertLessEqual(len(select_repetition_review_queue(first)), 20)

    def test_comparison_is_deterministic_and_observational(self):
        with tempfile.TemporaryDirectory() as tmp:
            analysis = analyze_repeated_experience(self.records(), self.make_db(Path(tmp)))
            compared = compare_repeated_experience(analysis, analysis)
            self.assertFalse(compared["production_change"])
            self.assertIn(compared["root_cause"], {
                "MIXED_REPETITION_PRESSURE", "STRUCTURAL_DUPLICATE_ACCUMULATION",
                "REPETITION_SIGNAL_MULTIPLICITY", "REPEATED_EXPERIENCE_DRIVES_FANOUT",
            })


if __name__ == "__main__":
    unittest.main()
