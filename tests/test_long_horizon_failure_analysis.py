import unittest

from long_horizon_failure_analysis import analyze, compare_turn, select_review_cases


def row(turn, selected, groups, candidates, precision=None):
    evaluation = {}
    if precision is not None:
        evaluation["working_memory_recall_precision"] = precision
    return {
        "turn": turn,
        "recall": {
            "selected_words": selected,
            "selected_thread_groups": groups,
            "activation_analysis": {"candidates": candidates},
        },
        "evaluation": evaluation,
    }


class LongHorizonFailureAnalysisTests(unittest.TestCase):
    def test_compare_turn_detects_structural_loss_without_semantic_labels(self):
        base = row(
            9982,
            ["話", "みつき"],
            ["みつき|青いマグカップ"],
            [
                {"word": "話", "rank": 1, "score": 100.0, "best_depth": 0, "frequency": 1800},
                {"word": "青いマグカップ", "rank": 17, "score": 1.0, "best_depth": 0, "frequency": 102},
                {"word": "みつき", "rank": 7, "score": 3.0, "best_depth": 2, "frequency": 1500},
            ],
            1.0,
        )
        virtual = row(
            9982,
            ["話"],
            [],
            [
                {"word": "話", "rank": 1, "score": 0.8, "best_depth": 0, "frequency": 1800},
                {"word": "青いマグカップ", "rank": 3, "score": 0.5, "best_depth": 0, "frequency": 102},
                {"word": "みつき", "rank": 10, "score": 0.001, "best_depth": 2, "frequency": 1500},
            ],
            0.5,
        )

        result = compare_turn(base, virtual)

        self.assertIn("THREAD_GROUP_LOSS", result["categories"])
        self.assertIn("DIRECT_INPUT_PRESENT_BUT_UNSELECTED", result["categories"])
        self.assertIn("TOP_SCORE_COLLAPSED_10X", result["categories"])
        self.assertIn("PRECISION_REGRESSION", result["categories"])
        self.assertIn("青いマグカップ", result["direct_unselected"])
        self.assertIn("青いマグカップ", [item["word"] for item in result["rank_shifts"]])

    def test_analyze_pairs_only_shared_turns(self):
        base = [row(1, ["A"], [], [], 1.0), row(2, ["B"], [], [], 1.0)]
        virtual = [row(2, [], [], [], 0.0), row(3, ["C"], [], [], 1.0)]

        result = analyze(base, virtual)

        self.assertEqual(result["shared_turn_count"], 1)
        self.assertEqual(result["changed_turn_count"], 1)
        self.assertEqual(result["comparisons"][0]["turn"], 2)
        self.assertIn("VIRTUAL_ABSTENTION_REGRESSION", result["comparisons"][0]["categories"])

    def test_review_selection_spreads_categories(self):
        comparisons = []
        for turn in range(1, 21):
            comparisons.append(
                {
                    "turn": turn,
                    "categories": ["SELECTION_CHANGED"] if turn < 15 else ["THREAD_GROUP_LOSS"],
                }
            )
        selected = select_review_cases(comparisons, limit=6)
        turns = {item["turn"] for item in selected}
        self.assertLessEqual(len(selected), 6)
        self.assertTrue(any(turn >= 15 for turn in turns))
        self.assertTrue(any(turn < 15 for turn in turns))


if __name__ == "__main__":
    unittest.main()
