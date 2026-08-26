import unittest

from trace_recall.terminal_aggregation import analyze_research_records, analyze_terminal_paths


class TerminalAggregationTests(unittest.TestCase):
    def test_identical_terminal_edges_are_aggregated_without_losing_provenance(self):
        paths = [
            {"from_type": "word", "from_id": "チーズケーキ", "to_type": "thread", "to_id": "A", "depth": 3, "score": 0.1, "reason": "word->thread"},
            {"from_type": "word", "from_id": "チーズケーキ", "to_type": "thread", "to_id": "A", "depth": 3, "score": 0.2, "reason": "word->thread"},
            {"from_type": "word", "from_id": "チーズケーキ", "to_type": "thread", "to_id": "B", "depth": 3, "score": 0.3, "reason": "word->thread"},
            {"from_type": "thread", "from_id": "X", "to_type": "word", "to_id": "チーズケーキ", "depth": 2, "score": 1.0, "reason": "thread->word"},
        ]
        result = analyze_terminal_paths(paths)
        self.assertEqual(result["physical_terminal_path_count"], 3)
        self.assertEqual(result["distinct_terminal_edge_count"], 2)
        self.assertEqual(result["maximum_repeated_edge_multiplicity"], 2)
        self.assertTrue(result["numeric_equivalent"])
        self.assertTrue(result["provenance_preserved"])
        self.assertEqual(sum(len(x["contributors"]) for x in result["edges"]), 3)

    def test_non_terminal_paths_are_not_aggregated(self):
        result = analyze_terminal_paths([
            {"from_type": "word", "from_id": "x", "to_type": "thread", "to_id": "A", "depth": 1, "score": 1.0},
            {"from_type": "word", "from_id": "x", "to_type": "thread", "to_id": "A", "depth": 2, "score": 1.0},
        ])
        self.assertEqual(result["physical_terminal_path_count"], 0)
        self.assertEqual(result["distinct_terminal_edge_count"], 0)

    def test_research_record_analysis_is_offline_only(self):
        records = [{
            "turn": 938,
            "recall": {
                "activation_analysis": {
                    "paths": [
                        {"from_type": "word", "from_id": "帰り", "to_type": "thread", "to_id": "T", "depth": 3, "score": 0.1},
                        {"from_type": "word", "from_id": "帰り", "to_type": "thread", "to_id": "T", "depth": 3, "score": 0.2},
                    ],
                    "candidates": [{"word": "帰り"}],
                },
                "selected_thread_groups": [],
                "selected_words": [{"word": "帰り"}],
            },
        }]
        result = analyze_research_records(records)
        self.assertEqual(result["judgement"], "TERMINAL_ARITHMETIC_EQUIVALENT")
        self.assertFalse(result["full_downstream_replay_performed"])
        self.assertEqual(result["turns"][0]["turn"], 938)
        self.assertEqual(result["turns"][0]["physical_terminal_path_count"], 2)
        self.assertEqual(result["turns"][0]["distinct_terminal_edge_count"], 1)

    def test_research_record_accepts_string_form_selected_groups(self):
        records = [{
            "turn": 10,
            "recall": {
                "activation_analysis": {
                    "paths": [
                        {"from_type": "word", "from_id": "カフェ", "to_type": "thread", "to_id": "T", "depth": 3, "score": 0.1},
                    ],
                    "candidates": ["カフェ"],
                },
                "selected_thread_groups": ["カフェ|帰り"],
                "selected_words": ["カフェ"],
            },
        }]
        result = analyze_research_records(records)
        row = result["turns"][0]
        self.assertEqual(row["observed_candidate_order"], ["カフェ"])
        self.assertEqual(row["observed_selected_thread_groups"], ["カフェ|帰り"])
        self.assertEqual(row["observed_selected_words"], ["カフェ"])


if __name__ == "__main__":
    unittest.main()
