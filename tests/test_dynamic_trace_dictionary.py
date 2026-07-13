import argparse
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from threaded_concept_memory_probe import (  # noqa: E402
    ThreadedConceptMemoryStore,
    build_components,
    extract_normalized_words,
)
from trace_recall.extractors.base import ExtractedWord  # noqa: E402


class DynamicTraceDictionaryStoreTests(unittest.TestCase):
    def test_store_vocabulary_cache_invalidates_after_db_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ThreadedConceptMemoryStore(str(Path(tmp) / "trace.sqlite"))
            try:
                store.create_thread([ExtractedWord("AIKanojyo", 1.0)], "AIKanojyo", created_by="user")
                first = store.get_trace_vocabulary()
                second = store.get_trace_vocabulary()
                self.assertEqual(first, second)
                store.create_thread([ExtractedWord("長期記憶", 1.0)], "長期記憶", created_by="user")
                refreshed = store.get_trace_vocabulary()
                self.assertIn(("長期記憶", refreshed[0][1]), refreshed)
            finally:
                store.close()

    def test_local_rule_uses_existing_trace_db_without_new_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "trace.sqlite"
            store = ThreadedConceptMemoryStore(str(db))
            try:
                store.create_thread([ExtractedWord("OPPO Reno9", 1.0), ExtractedWord("長期記憶", 1.0)], "seed", created_by="user")
            finally:
                store.close()

            args = argparse.Namespace(
                db=str(db), extractor="local-rule", debug_extractor=False, base_url="", api_key="",
                model="local-model", extractor_model="", timeout=0.01, half_life_days=30.0,
                max_depth=2, common_bonus=0.5, mutual_amplification=0.3, thread_strength_mode="count",
            )
            store, extractor, _engine, _generator = build_components(args)
            try:
                words = {item.word for item in extract_normalized_words(args, extractor, "OPPO Reno9で長期記憶を実装した", "user")}
                self.assertTrue({"OPPO Reno9", "長期記憶"} <= words)
                tables = {row[0] for row in sqlite3.connect(db).execute("SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertEqual({"words", "threads", "conversation_exposures", "word_threads"}, tables)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
