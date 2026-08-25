import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trace_recall.gate_pressure import (  # noqa: E402
    analyze_gate_pressure, compare_gate_pressure, select_pressure_review_turns,
)


def record(turn=1, accepted=True, path_count=1, depth=2, frequency=12):
    paths = [{"from_type": "thread", "from_id": f"t{index % 2}", "to_type": "word", "to_id": "memory", "depth": depth, "score": .1, "reason": "thread->word"} for index in range(path_count)]
    paths.append({"from_type": "input", "from_id": "cue", "to_type": "thread", "to_id": "t0", "depth": 1, "score": 1.0, "reason": "input->thread"})
    events = [
        {"stage": "RAW_ACTIVATION", "identifier": "memory", "accepted": True, "reason": "raw activation candidate"},
        {"stage": "ACTIVATION_GATE", "identifier": "memory", "accepted": accepted, "reason": "selected" if accepted else "below gate or outside selected threads", "input_score": .1},
        {"stage": "RECALL_SELECTION", "identifier": "memory", "accepted": accepted, "reason": "propagated"},
        {"stage": "WORKING_MEMORY", "identifier": "memory", "accepted": accepted, "reason": "included" if accepted else "propagated"},
    ]
    return {"schema_version": 2, "turn": turn, "recall": {"selected_words": ["memory"] if accepted else [], "stage_diagnostics": events, "activation_analysis": {"candidates": [{"word": "memory", "score": .1, "best_depth": depth, "frequency": frequency, "activation_sources": ["thread:t0"], "thread_ids": ["t0", "t1"]}], "paths": paths, "threads": {"t0": {"canonical_key": "family"}, "t1": {"canonical_key": "family"}}}}, "evaluation": {"expected_words": ["memory"], "unexpected_words": [], "unexpected_hit_count": 0}, "governance_observation_config": {"gate_min_word_score": .05}, "timing": {"recall_ms": 2.0, "llm_response_ms": 0.0, "total_ms": 3.0}}


class GatePressureTests(unittest.TestCase):
    def test_depth_path_frequency_redundancy_and_downstream_reject(self):
        result = analyze_gate_pressure([record(1, False, 5, 3, 120)])
        self.assertEqual(result["candidate_pressure"]["gate_suppressed"], 1)
        self.assertEqual(result["propagation_depth"]["3+"]["candidate_count"], 1)
        self.assertEqual(result["path_multiplicity"]["5-9"]["candidate_count"], 1)
        self.assertEqual(result["frequency_pressure"]["100+"]["activation_count"], 1)
        self.assertEqual(result["redundancy"]["duplicate_path_ratio"], 1.0)
        self.assertEqual(result["suppression_causes"], {"UNCLASSIFIED": 1})

    def test_aggregation_is_deterministic_and_observational(self):
        rows = [record(turn, turn % 2 == 0, turn % 6 + 1, turn % 4, turn) for turn in range(1, 35)]
        untouched = copy.deepcopy(rows)
        first = analyze_gate_pressure(rows)
        self.assertEqual(first, analyze_gate_pressure(rows))
        self.assertEqual(rows, untouched)
        self.assertIn("GATE", first["unavailable_latency_stages"])
        self.assertEqual(first["correlations"]["candidate_count_vs_processing_time"]["sample_count"], 34)

    def test_comparison_and_review_queue(self):
        short = analyze_gate_pressure([record(turn, True, 1, 1, 2) for turn in range(1, 31)])
        long = analyze_gate_pressure([record(turn, turn % 3 == 0, 5, 2, 100) for turn in range(1, 41)])
        comparison = compare_gate_pressure(short, long)
        self.assertIn(comparison["root_cause"], {"PATH_EXPLOSION", "FREQUENCY_PRESSURE", "REDUNDANT_CANDIDATES", "GATE_CAPACITY_PRESSURE", "MIXED_PRESSURE", "INSUFFICIENT_EVIDENCE"})
        queue = select_pressure_review_turns(long, 20)
        self.assertLessEqual(len(queue), 20)
        self.assertTrue(all(row["expectation"] == "MAY_RECALL" and row["annotation_status"] == "REVIEW_REQUIRED" for row in queue))


if __name__ == "__main__":
    unittest.main()
