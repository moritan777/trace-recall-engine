import copy
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trace_recall.path_growth import analyze_path_origin, compare_path_origin, select_path_review_queue, thread_signature


class PathGrowthTest(unittest.TestCase):
    def make_db(self, root: Path) -> Path:
        path = root / "memory.db"
        with sqlite3.connect(path) as db:
            db.executescript("""
            CREATE TABLE threads(thread_id TEXT, canonical_key TEXT, created_by TEXT, created_at TEXT, seen_count INTEGER);
            CREATE TABLE words(word_id TEXT, word TEXT, seen_count INTEGER);
            CREATE TABLE word_threads(word_id TEXT, thread_id TEXT);
            """)
            db.executemany("INSERT INTO words VALUES(?,?,?)", [("w1","coffee",12),("w2","cafe",3),("w3","tea",2)])
            db.executemany("INSERT INTO threads VALUES(?,?,?,?,?)", [("t1","a","user","2025-01-01T00:00:00",2),("t2","b","user","2025-01-02T00:00:00",1),("t3","c","user","2025-01-03T00:00:00",1)])
            db.executemany("INSERT INTO word_threads VALUES(?,?)", [("w1","t1"),("w2","t1"),("w1","t2"),("w2","t2"),("w1","t3"),("w3","t3")])
        return path

    def rows(self):
        return [{"turn": n, "recall": {"selected_words": ["coffee"], "activation_analysis": {"candidates": [{"word":"coffee","frequency":12},{"word":"tea","frequency":2}], "paths": [{"from_type":"thread","from_id":"t1","to_type":"word","to_id":"coffee"},{"from_type":"thread","from_id":"t2","to_type":"word","to_id":"coffee"},{"from_type":"word","from_id":"coffee","to_type":"thread","to_id":"t3"}]}, "stage_diagnostics": [{"stage":"ACTIVATION_GATE","identifier":"coffee","accepted":True},{"stage":"ACTIVATION_GATE","identifier":"tea","accepted":False}]}, "evaluation": {"expected_words":["coffee"],"unexpected_words":[],"expected_hit_count":1}, "timing":{"total_ms":float(n)}} for n in range(1, 31)]

    def test_signature_is_deterministic_and_distinguishes_origin(self):
        self.assertEqual(thread_signature(["b","a","a"], "user"), thread_signature(["a","b"], "user"))
        self.assertNotEqual(thread_signature(["a","b"], "user"), thread_signature(["a","b"], "assistant"))

    def test_complete_deterministic_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = self.make_db(Path(tmp)); rows = self.rows(); original = copy.deepcopy(rows)
            first = analyze_path_origin(rows, db); second = analyze_path_origin(rows, db)
            self.assertEqual(first, second); self.assertEqual(rows, original)
            self.assertEqual(first["thread_creation"]["unique_thread_signatures"], 2)
            self.assertEqual(first["thread_creation"]["exact_duplicate_thread_count"], 1)
            self.assertEqual(first["same_word_multi_thread"][0]["contributing_threads"], 3)
            self.assertIn("1-4", first["fanout_distribution"])
            self.assertEqual(first["path_amplification"]["connections_traversed_per_candidate"], 1.5)
            self.assertEqual(len(first["historical_accumulation"]), 5)
            self.assertEqual(first["path_concentration"]["top_20_percent"]["connections_traversed_share"], 1/3)
            self.assertEqual(first["useful_path_coverage"]["expected_target_paths"], 60)
            self.assertEqual(first["connection_growth"]["traversed_path_types"]["thread->word"], 60)
            self.assertLessEqual(len(select_path_review_queue(first)), 20)
            compared = compare_path_origin(first, first)
            self.assertEqual(compared["root_cause"], "INSUFFICIENT_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
