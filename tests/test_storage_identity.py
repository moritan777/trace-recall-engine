import copy
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trace_recall.storage_identity import (
    analyze_storage_identity,
    compare_storage_identity,
    select_storage_identity_review_queue,
)


class StorageIdentityTests(unittest.TestCase):
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
                ("w1", "coffee", 2, 1, 9, "a", "z"),
                ("w2", "cafe", 1, 1, 4, "a", "z"),
            ])
            db.executemany("INSERT INTO threads VALUES(?,?,?,?,?,?,?,?,?)", [
                ("t1", "2025-01-01", "coffee at cafe", "k", 1, "2025-01-01T01:00", "2025-01-01T01:00", 1, "user"),
                ("t2", "2025-01-01", "coffee at cafe", "k", 2, "2025-01-01T02:00", "2025-01-02T02:00", 2, "user"),
                ("t3", "2025-01-02", "another coffee at cafe", "k", 1, "2025-01-02T01:00", "2025-01-02T01:00", 1, "assistant"),
            ])
            db.executemany("INSERT INTO word_threads VALUES(?,?,?,?)", [
                (word, thread, 1, "x") for thread in ("t1", "t2", "t3") for word in ("w1", "w2")
            ])
        return path

    def records(self, expected="coffee"):
        return [{
            "turn": turn,
            "recall": {
                "selected_words": ["coffee"],
                "activation_analysis": {"paths": [
                    {"from_type": "thread", "from_id": thread, "to_type": "word", "to_id": "coffee"}
                    for thread in ("t1", "t2", "t3")
                ]},
                "stage_diagnostics": [{"stage": "ACTIVATION_GATE", "identifier": "coffee", "accepted": True}],
            },
            "evaluation": {"expected_words": [expected], "unexpected_words": []},
        } for turn in range(1, 31)]

    def test_identity_levels_artifact_over_separation_and_differences(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self.make_db(Path(tmp)); records = self.records(); original = copy.deepcopy(records)
            first = analyze_storage_identity(records, db)
            self.assertEqual(first, analyze_storage_identity(records, db))
            self.assertEqual(records, original)
            self.assertEqual(first["identity_levels"]["LEVEL_0_WORD_SET"]["unique_identity_count"], 1)
            self.assertEqual(first["identity_levels"]["LEVEL_1_SOURCE_TEXT"]["unique_identity_count"], 2)
            self.assertEqual(first["identity_levels"]["LEVEL_3_TEMPORAL_STATE"]["unique_identity_count"], 3)
            self.assertTrue(first["identity_levels"]["LEVEL_3_TEMPORAL_STATE"]["over_separating"])
            self.assertEqual(first["temporal_identity_review"]["classification"], "TIMESTAMP_UNIQUENESS_ARTIFACT")
            self.assertEqual(first["state_difference_causes"]["source_text"], 1)
            self.assertEqual(first["connection_set_equivalence"]["IDENTICAL_CONNECTION_SET"], 1)
            model = first["offline_identity_counterfactuals"]["MODEL_B_STRUCTURAL_IDENTITY"]
            self.assertEqual(model["marker"], "OFFLINE_IDENTITY_COUNTERFACTUAL")
            self.assertFalse(model["production_replay"])
            self.assertEqual(model["estimated_thread_identities"], 1)
            self.assertEqual(model["estimated_connections"], 2)
            self.assertLessEqual(len(select_storage_identity_review_queue(first)), 20)

    def test_expected_label_is_not_used_for_identity_and_inputs_are_observational(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self.make_db(Path(tmp))
            expected = analyze_storage_identity(self.records("coffee"), db)
            changed = analyze_storage_identity(self.records("not-present"), db)
            self.assertEqual(expected["identity_levels"], changed["identity_levels"])
            self.assertEqual(expected["identity_split_matrix"], changed["identity_split_matrix"])
            self.assertFalse(expected["integrity"]["target_or_expected_label_used_for_identity"])
            comparison = compare_storage_identity(expected, expected)
            self.assertFalse(comparison["production_migration"])
            self.assertIn(comparison["identity_classification"], {
                "MIXED_IDENTITY_PROBLEM", "IDENTITY_TOO_COARSE", "IDENTITY_AND_STATE_CONFLATED",
            })


if __name__ == "__main__":
    unittest.main()
