import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trace_recall.governance_capture import (  # noqa: E402
    build_activation_path_analyses, build_failure_audits, capture_record, convert_research_records, evaluate_governance, load_annotations,
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
        annotation = {2: {"expectation": "SHOULD_RECALL", "words": ["memory"], "benchmark_responsibility": "ASSOCIATIVE_RECALL_EXPECTED"}}
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
            path.write_text('{"turn":2,"expectation":"should_recall","words":["memory"],"benchmark_responsibility":"ASSOCIATIVE_RECALL_EXPECTED"}\n', encoding="utf-8")
            rows = convert_research_records([research(1), research(2)], load_annotations(path))
        result = evaluate_governance(rows)
        self.assertEqual(result["annotation_count"], 1)
        self.assertEqual(result["expectation_denominators"], {"SHOULD_RECALL": 1})
        self.assertEqual(result["should_recall_hit_rate"], 1.0)
        self.assertIsNone(result["must_not_speak_leakage"])

    def test_artificial_and_captured_use_same_evaluator(self):
        captured = convert_research_records([research()], {2: {"expectation": "SHOULD_RECALL", "words": ["memory"], "benchmark_responsibility": "ASSOCIATIVE_RECALL_EXPECTED"}})[0]
        artificial = {"observed": captured["observed"], "expectation": "SHOULD_RECALL", "words": ["memory"], "benchmark_responsibility": "ASSOCIATIVE_RECALL_EXPECTED"}
        self.assertEqual(evaluate_governance([captured])["should_recall_hit_rate"], evaluate_governance([artificial])["should_recall_hit_rate"])

    def test_candidate_propagation_is_not_three_turn_failures(self):
        row = research()
        row["recall"]["selected_words"] = []
        row["recall"]["stage_diagnostics"] = [
            {"stage": "RAW_ACTIVATION", "identifier": "memory", "accepted": True},
            {"stage": "ACTIVATION_GATE", "identifier": "memory", "accepted": False},
            {"stage": "RECALL_SELECTION", "identifier": "memory", "accepted": False},
            {"stage": "WORKING_MEMORY", "identifier": "memory", "accepted": False},
        ]
        result = evaluate_governance(convert_research_records([row], {2: {"expectation": "SHOULD_RECALL", "words": ["memory"], "benchmark_responsibility": "ASSOCIATIVE_RECALL_EXPECTED"}}))
        self.assertEqual(result["candidate_observations_by_stage"], {"ACTIVATION_GATE": 1, "RAW_ACTIVATION": 1, "RECALL_SELECTION": 1, "WORKING_MEMORY": 1})
        self.assertEqual(result["candidate_suppressions_by_stage"], {"ACTIVATION_GATE": 1})
        self.assertEqual(result["turn_level_root_cause_failures"], {"ACTIVATION_GATE": 1})

    def test_unobserved_response_does_not_claim_must_not_speak_success(self):
        row = research()
        row["response"] = {"enabled": False, "skipped": True, "text": ""}
        result = evaluate_governance(convert_research_records([row], {2: {"expectation": "MUST_NOT_SPEAK", "words": ["secret"]}}))
        self.assertEqual(result["annotation_counts"], {"MUST_NOT_SPEAK": 1})
        self.assertNotIn("MUST_NOT_SPEAK", result["expectation_denominators"])
        self.assertIsNone(result["must_not_speak_leakage"])

    def test_failure_audit_records_gate_margin_and_root_cause(self):
        row = research()
        row["recall"]["selected_words"] = []
        row["recall"]["stage_diagnostics"] = [
            {"stage": "EXTRACTION", "identifier": "query", "accepted": True},
            {"stage": "RAW_ACTIVATION", "identifier": "memory", "accepted": True, "reason": "raw activation candidate", "output_score": 0.04, "activation_source": "thread:t1", "raw_frequency": 2, "reinforcement_contribution": 0.1},
            {"stage": "ACTIVATION_GATE", "identifier": "memory", "accepted": False, "reason": "below gate", "input_score": 0.04, "output_score": 0.0},
            {"stage": "RECALL_SELECTION", "identifier": "memory", "accepted": False, "reason": "below gate"},
            {"stage": "WORKING_MEMORY", "identifier": "memory", "accepted": False, "reason": "below gate"},
        ]
        captured = convert_research_records([row], {2: {"expectation": "SHOULD_RECALL", "words": ["memory"], "benchmark_responsibility": "ASSOCIATIVE_RECALL_EXPECTED"}})
        audit = build_failure_audits(captured, 0.05)[0]
        self.assertAlmostEqual(audit["targets"][0]["score_minus_gate_threshold"], -0.01)
        self.assertEqual(audit["targets"][0]["classification"], "gate suppression")

    def test_activation_path_analysis_separates_path_components_and_competition(self):
        captured = convert_research_records([research()], {2: {"expectation": "SHOULD_RECALL", "words": ["missing"], "benchmark_responsibility": "ASSOCIATIVE_RECALL_EXPECTED"}})[0]
        captured["observed"]["activation_analysis"] = {
            "candidates": [{"rank": 1, "word": "rival", "score": 1.0, "activation_sources": ["input:q"]}, {"rank": 2, "word": "missing", "score": 0.2, "best_depth": 2, "activation_sources": ["thread:t"]}],
            "paths": [{"from_type": "thread", "from_id": "t", "to_type": "word", "to_id": "missing", "depth": 2, "score": 0.2, "reason": "thread->word"}],
            "expected_target_db": {"missing": {"word_exists": True, "word_strength": 2.0, "frequency": 4, "linked_threads": [{"thread_id": "t", "thread": {"created_by": "user"}}]}},
            "depth_decay": {"2": 0.15},
        }
        target = build_activation_path_analyses([captured])[0]["targets"][0]
        self.assertEqual(target["propagated_activation"], 0.2)
        self.assertAlmostEqual(target["counterfactual"]["hypothetical_no_frequency_reinforcement_score"], 0.1)
        self.assertEqual(target["competing_candidates"][0]["candidate"], "rival")

    def test_stable_fact_is_excluded_from_associative_denominator(self):
        rows = convert_research_records(
            [research(1), research(2)],
            {
                1: {"expectation": "SHOULD_RECALL", "words": ["memory"], "benchmark_responsibility": "ASSOCIATIVE_RECALL_EXPECTED"},
                2: {"expectation": "SHOULD_RECALL", "words": ["exact-date"], "benchmark_responsibility": "STABLE_FACT_EXPECTED"},
            },
        )
        result = evaluate_governance(rows)
        self.assertEqual(result["expectation_denominators"], {"SHOULD_RECALL": 1})
        self.assertEqual(result["associative_should_recall_hit_rate"], 1.0)
        self.assertEqual(result["stable_fact_coverage_observation"], {"hits": 0, "total": 1, "rate": 0.0})


if __name__ == "__main__":
    unittest.main()
