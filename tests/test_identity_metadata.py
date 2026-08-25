import copy
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trace_recall.identity_metadata import analyze_identity_metadata, select_identity_metadata_review_queue


class IdentityMetadataTests(unittest.TestCase):
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
                ("w2", "cafe", 1, 1, 4, "a", "z"),
                ("w3", "tea", 1, 1, 2, "a", "z"),
            ])
            db.executemany("INSERT INTO threads VALUES(?,?,?,?,?,?,?,?,?)", [
                ("t1", "2025-01-01", "coffee at cafe", "k", 1, "2025-01-01T00:00:00", "2025-01-01T00:00:00", 1, "user"),
                ("t2", "2025-01-01", "coffee at cafe", "k", 1, "2025-01-01T00:00:00", "2025-01-01T00:00:00", 1, "user"),
                ("t3", "2025-01-01", "cafe serves coffee", "k", 1, "2025-01-01T00:00:01", "2025-01-01T00:00:01", 1, "user"),
                ("t4", "2025-01-01", "tea", "q", 1, "2025-01-01T00:00:02", "2025-01-01T00:00:02", 1, "user"),
            ])
            db.executemany("INSERT INTO word_threads VALUES(?,?,?,?)", [
                (word, thread, 1, "x") for thread in ("t1", "t2", "t3") for word in ("w1", "w2")
            ] + [("w3", "t4", 1, "x")])
        return path

    def conversation(self):
        return [
            {"turn": 1, "mode": "learn", "text": "coffee at cafe", "role": "user"},
            {"turn": 2, "mode": "learn", "text": "coffee at cafe", "role": "user"},
            {"turn": 3, "mode": "learn", "text": "cafe serves coffee", "role": "user"},
            {"turn": 4, "mode": "learn", "text": "tea", "role": "user"},
            {"turn": 5, "mode": "ask", "text": "drink?", "role": "user"},
        ]

    def test_provenance_mapping_duplication_repetition_and_counterfactual(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self.make_db(Path(tmp)); conversation = self.conversation(); logs = [{"turn": 5}]
            original_conversation = copy.deepcopy(conversation); original_logs = copy.deepcopy(logs)
            first = analyze_identity_metadata(conversation, logs, db)
            self.assertEqual(first, analyze_identity_metadata(conversation, logs, db))
            self.assertEqual(conversation, original_conversation); self.assertEqual(logs, original_logs)
            self.assertEqual(first["source_mapping"]["mapping_coverage"], 1.0)
            self.assertEqual(first["intra_turn_duplication"]["classification"], "NO_INTRA_TURN_DUPLICATION_OBSERVED")
            self.assertEqual(first["inter_turn_repetition"]["classification"], "INTER_TURN_REPETITION")
            self.assertEqual(first["inter_turn_repetition"]["same_exact_input_groups"], 1)
            self.assertEqual(first["inter_turn_repetition"]["different_source_same_word_set_groups"], 1)
            self.assertEqual(first["source_turn_counterfactual"]["marker"], "OFFLINE_METADATA_COUNTERFACTUAL")
            self.assertEqual(first["source_turn_counterfactual"]["unique_identities"], 4)
            self.assertEqual(first["source_turn_counterfactual"]["repeat_instances"], 0)
            self.assertEqual(first["source_message_counterfactual"]["status"], "UNAVAILABLE")
            self.assertEqual(first["session_identity"]["status"], "UNAVAILABLE")
            self.assertLessEqual(len(select_identity_metadata_review_queue(first)), 20)

    def test_timestamp_mutable_state_policy_and_observational_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            analysis = analyze_identity_metadata(self.conversation(), [{"turn": 5}], self.make_db(Path(tmp)))
            self.assertEqual(analysis["temporal_metadata_audit"]["created_at_classification"], "STORAGE_TIME")
            self.assertEqual(analysis["temporal_metadata_audit"]["precision"], "seconds (now_iso timespec=seconds)")
            self.assertGreater(analysis["temporal_metadata_audit"]["same_timestamp_collision_count"], 0)
            self.assertEqual(analysis["mutable_state_audit"]["threads.seen_count"]["classification"], "MUTABLE_STATE")
            self.assertEqual(analysis["thread_creation_policy"]["reuse_classification_for_analyzed_baseline"], "NO_REUSE")
            self.assertEqual(analysis["root_cause"], "MULTIPLE_IDENTITY_GAPS")
            self.assertEqual(analysis["recommended_metadata_direction"], "SEPARATE_DESCRIPTION_AND_OCCURRENCE")
            self.assertFalse(analysis["integrity"]["production_schema_change"])


if __name__ == "__main__":
    unittest.main()
