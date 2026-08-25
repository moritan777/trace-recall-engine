import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trace_recall.governance_capture import (  # noqa: E402
    capture_record, convert_research_records, evaluate_governance, load_annotations,
)


def research(turn=2):
    return {
        "schema_version": 2, "turn": turn, "mode": "ask", "input_text": "hello",
        "recall": {"outcome": "CANDIDATES_SELECTED", "activated_threads": ["c1"], "selected_words": ["memory"], "topic_reentry_words": [], "stage_diagnostics": [{"stage": "ACTIVATION_GATE", "identifier": "memory", "accepted": True, "input_score": 1.2, "raw_frequency": 3}]},
        "working_memory": {"word_count": 1, "thread_group_count": 1, "selected_thread_groups": []},
        "prompt": {"rough_tokens": 12}, "evaluation": {"precision_like": 1.0},
    }


class GovernanceCaptureTests(unittest.TestCase):
    def test_schema_v2_conversion_is_deterministic_and_separates_annotation(self):
        annotation = {2: {"expectation": "SHOULD_RECALL", "words": ["memory"]}}
        first = convert_research_records([research()], annotation)
        self.assertEqual(first, convert_research_records([research()], annotation))
        self.assertEqual(first[0]["observed"]["candidate_ids"], ["c1"])
        self.assertNotIn("expectation", first[0]["observed"])
        self.assertEqual(first[0]["annotation"]["expectation"], "SHOULD_RECALL")

    def test_missing_optional_fields_are_safe(self):
        row = capture_record({"schema_version": 2, "turn": 1})
        self.assertEqual(row["observed"]["diagnostic_stage_events"], [])
        self.assertNotIn("annotation", row)

    def test_overlay_and_unannotated_denominators(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "annotations.jsonl"
            path.write_text('{"turn":2,"expectation":"should_recall","words":["memory"]}\n', encoding="utf-8")
            rows = convert_research_records([research(1), research(2)], load_annotations(path))
        result = evaluate_governance(rows)
        self.assertEqual(result["annotation_count"], 1)
        self.assertEqual(result["expectation_denominators"], {"SHOULD_RECALL": 1})
        self.assertEqual(result["should_recall_hit_rate"], 1.0)
        self.assertIsNone(result["must_not_speak_leakage"])

    def test_artificial_and_captured_use_same_evaluator(self):
        captured = convert_research_records([research()], {2: {"expectation": "SHOULD_RECALL", "words": ["memory"]}})[0]
        artificial = {"observed": captured["observed"], "expectation": "SHOULD_RECALL", "words": ["memory"]}
        self.assertEqual(evaluate_governance([captured])["should_recall_hit_rate"], evaluate_governance([artificial])["should_recall_hit_rate"])


if __name__ == "__main__":
    unittest.main()
