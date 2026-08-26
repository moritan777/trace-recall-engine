import tempfile
import unittest
from pathlib import Path

import threaded_concept_memory_probe as probe
from terminal_aggregation_runtime import TerminalAggregationActivationEngine


class TerminalAggregationRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "memory.db")
        self.store = probe.ThreadedConceptMemoryStore(self.db)
        for words in [
            ["カフェ", "チーズケーキ", "帰り"],
            ["カフェ", "コーヒー", "帰り"],
            ["カフェ", "チーズケーキ", "また"],
            ["帰り", "また", "映画"],
            ["帰り", "チーズケーキ", "映画"],
        ]:
            self.store.create_thread([probe.ExtractedWord(w, 1.0) for w in words], " ".join(words), "count", "user")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_runtime_prototype_preserves_recall_and_gate_results(self):
        baseline = probe.ActivationEngine(self.store, half_life_days=10_000, max_depth=3, thread_strength_mode="count")
        prototype = TerminalAggregationActivationEngine(self.store, half_life_days=10_000, max_depth=3, thread_strength_mode="count")
        query = [probe.ExtractedWord("カフェ", 1.0), probe.ExtractedWord("帰り", 1.0)]

        a = baseline.activate(query, top_words=20, top_threads=20)
        b = prototype.activate(query, top_words=20, top_threads=20)

        self.assertEqual([x.word for x in a.activated_words], [x.word for x in b.activated_words])
        self.assertEqual([x.thread_id for x in a.activated_threads], [x.thread_id for x in b.activated_threads])
        for left, right in zip(a.activated_words, b.activated_words):
            self.assertAlmostEqual(left.score, right.score, places=12)
            self.assertEqual(left.best_depth, right.best_depth)
            self.assertEqual(left.thread_ids, right.thread_ids)
        for left, right in zip(a.activated_threads, b.activated_threads):
            self.assertAlmostEqual(left.score, right.score, places=12)
            self.assertAlmostEqual(left.base_score, right.base_score, places=12)
            self.assertAlmostEqual(left.common_bonus, right.common_bonus, places=12)

        gate_a = probe.ActivationGate(store=self.store).gate(a)
        gate_b = probe.ActivationGate(store=self.store).gate(b)
        self.assertEqual([x.canonical_key for x in gate_a.threads], [x.canonical_key for x in gate_b.threads])
        self.assertEqual([x.word for x in gate_a.words], [x.word for x in gate_b.words])
        self.assertEqual([x.word for x in gate_a.suppressed_words], [x.word for x in gate_b.suppressed_words])
        self.assertEqual(gate_a.outcome, gate_b.outcome)
        self.assertEqual(gate_a.topic_reentry_words, gate_b.topic_reentry_words)

    def test_runtime_prototype_reduces_terminal_edge_work(self):
        prototype = TerminalAggregationActivationEngine(self.store, half_life_days=10_000, max_depth=3, thread_strength_mode="count")
        query = [probe.ExtractedWord("カフェ", 1.0), probe.ExtractedWord("帰り", 1.0)]
        prototype.activate(query, top_words=20, top_threads=20)
        stats = prototype.last_terminal_aggregation_stats
        self.assertGreater(stats.physical_terminal_paths, 0)
        self.assertGreater(stats.distinct_terminal_edges, 0)
        self.assertGreaterEqual(stats.physical_terminal_paths, stats.distinct_terminal_edges)
        self.assertGreaterEqual(stats.maximum_edge_multiplicity, 1)
        self.assertEqual(stats.operations_saved, stats.physical_terminal_paths - stats.distinct_terminal_edges)

    def test_default_engine_is_still_default_off(self):
        baseline = probe.ActivationEngine(self.store, max_depth=3, thread_strength_mode="count")
        result = baseline.activate([probe.ExtractedWord("カフェ", 1.0)])
        self.assertFalse(hasattr(baseline, "last_terminal_aggregation_stats"))
        self.assertFalse(hasattr(result, "terminal_aggregation_stats"))


if __name__ == "__main__":
    unittest.main()
