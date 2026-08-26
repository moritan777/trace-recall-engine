import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from terminal_aggregation_replay import analyze_downstream_replay, iter_research_records


class TerminalAggregationDownstreamReplayTests(unittest.TestCase):
    def _record(self):
        return {
            "turn": 10,
            "extractor": {
                "normalized_words": [{"word": "x", "weight": 1.0}],
            },
            "governance_observation_config": {
                "gate_min_word_score": 0.05,
                "fatigue_recent_turns": 10,
                "fatigue_threshold": 3,
            },
            "recall": {
                "activated_words": ["x", "y"],
                "activated_threads": ["T"],
                "selected_thread_groups": ["x|y"],
                "selected_words": ["x", "y"],
                "fatigue_suppressed_words": [],
                "outcome": "CANDIDATES_SELECTED",
                "topic_reentry_words": [],
                "stage_diagnostics": [],
                "activation_analysis": {
                    "candidates": [
                        {
                            "rank": 1,
                            "word": "x",
                            "score": 1.0,
                            "best_depth": 0,
                            "thread_ids": ["T"],
                            "activation_sources": ["input:x"],
                        },
                        {
                            "rank": 2,
                            "word": "y",
                            "score": 0.2,
                            "best_depth": 2,
                            "thread_ids": ["T"],
                            "activation_sources": ["thread:T"],
                        },
                    ],
                    "paths": [
                        {
                            "from_type": "input",
                            "from_id": "x",
                            "to_type": "word",
                            "to_id": "x",
                            "depth": 0,
                            "score": 1.0,
                            "reason": "matched sim=1.00",
                        },
                        {
                            "from_type": "word",
                            "from_id": "x",
                            "to_type": "thread",
                            "to_id": "T",
                            "depth": 1,
                            "score": 0.4,
                            "reason": "word->thread",
                        },
                        {
                            "from_type": "thread",
                            "from_id": "T",
                            "to_type": "word",
                            "to_id": "y",
                            "depth": 2,
                            "score": 0.2,
                            "reason": "thread->word",
                        },
                        {
                            "from_type": "word",
                            "from_id": "y",
                            "to_type": "thread",
                            "to_id": "T",
                            "depth": 3,
                            "score": 0.05,
                            "reason": "word->thread",
                        },
                        {
                            "from_type": "word",
                            "from_id": "y",
                            "to_type": "thread",
                            "to_id": "T",
                            "depth": 3,
                            "score": 0.05,
                            "reason": "word->thread",
                        },
                    ],
                    "threads": {
                        "T": {
                            "words": ["x", "y"],
                            "canonical_key": "x|y",
                            "created_by": "user",
                            "strength": 1.0,
                        }
                    },
                },
            },
            "working_memory": {
                "selected_words": ["x", "y"],
            },
        }

    def test_terminal_aggregation_replays_gate_and_working_memory_equivalently(self):
        result = analyze_downstream_replay([self._record()])
        self.assertEqual(result["judgement"], "TERMINAL_AGGREGATION_DOWNSTREAM_EQUIVALENT")
        self.assertTrue(result["full_downstream_replay_performed"])
        self.assertTrue(result["numeric_equivalent_all_turns"])
        self.assertTrue(result["provenance_preserved_all_turns"])
        self.assertTrue(result["downstream_equivalent_all_turns"])
        turn = result["turns"][0]
        self.assertEqual(turn["physical_terminal_path_count"], 2)
        self.assertEqual(turn["distinct_terminal_edge_count"], 1)
        self.assertTrue(turn["selected_thread_groups_equal"])
        self.assertTrue(turn["gate_words_equal"])
        self.assertTrue(turn["working_memory_words_equal"])
        self.assertTrue(all(turn["baseline_observation_fidelity"].values()))

    def test_zip_reader_streams_single_jsonl_member(self):
        record = self._record()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "research.zip"
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("research.jsonl", json.dumps(record, ensure_ascii=False) + "\n")
            loaded = list(iter_research_records(path))
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["turn"], 10)


if __name__ == "__main__":
    unittest.main()
