import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import threaded_concept_memory_probe as probe
from trace_recall.diagnostics import DiagnosticRecorder
from trace_recall.extractors.base import ExtractedWord
from trace_recall.governance import AdmissionAction, AdmissionDecision


class EvaluationDiagnosticsTests(unittest.TestCase):
    def test_no_response_efficiency_is_not_applicable(self):
        activation = probe.ActivationResult([], [], [], [])
        gated = probe.GatedContext([], [], [], "empty")

        metrics = probe.evaluate_recall_turn(
            turn=1,
            mode="ask_no_response",
            expected_words=["expected"],
            unexpected_words=["unexpected"],
            activation=activation,
            gated=gated,
            prompt="",
            response_text="",
            response_skipped=True,
        )

        self.assertIsNone(metrics["recall_efficiency"])
        self.assertEqual(
            metrics["recall_efficiency_status"],
            "not_applicable_no_response",
        )
        self.assertEqual(
            metrics["recall_precision_like_scope"],
            "working_memory_only_no_response",
        )

        flattened = probe.flatten_eval_metrics({"metrics": metrics})
        self.assertEqual(flattened["recall_efficiency"], "N/A")
        self.assertEqual(
            flattened["recall_efficiency_status"],
            "not_applicable_no_response",
        )

        summary = probe.build_eval_report_summary([flattened])
        self.assertTrue(
            any("average_recall_efficiency: N/A" in line for line in summary)
        )

    def test_response_enabled_efficiency_remains_numeric(self):
        metrics = probe.evaluate_recall_turn(
            turn=2,
            mode="ask",
            expected_words=[],
            unexpected_words=[],
            activation=probe.ActivationResult([], [], [], []),
            gated=probe.GatedContext([], [], [], "empty"),
            prompt="",
            response_text="",
            response_skipped=False,
        )
        self.assertEqual(metrics["recall_efficiency"], 0.0)
        self.assertEqual(metrics["recall_efficiency_status"], "measured")

    def test_external_admission_rejections_are_counted_separately(self):
        activation = probe.ActivationResult(
            input_words=[ExtractedWord("alpha", 1.0)],
            activated_words=[
                probe.ActivatedWord("alpha", 1.0, 0, ["thread-1"], ["alpha"]),
            ],
            activated_threads=[
                probe.ActivatedThread(
                    thread_id="thread-1",
                    score=1.0,
                    base_score=1.0,
                    common_bonus=0.0,
                    words=["alpha"],
                    matched_words=["alpha"],
                    activated_by=["alpha"],
                    date="2026-01-01",
                    canonical_key="alpha",
                )
            ],
            traces=[],
        )
        recorder = DiagnosticRecorder()
        gate = probe.ActivationGate(
            max_prompt_words=2,
            diagnostics=recorder,
            admission_hook=lambda candidate, context: AdmissionDecision(
                AdmissionAction.SUPPRESS, "external policy"
            ),
        )
        gated = gate.gate(activation)
        self.assertEqual(gated.words, [])
        events = recorder.to_jsonable()
        admission = [
            event for event in events
            if event["stage"] == "EXTERNAL_ADMISSION"
        ]
        self.assertEqual(len(admission), 1)
        self.assertFalse(admission[0]["accepted"])
        self.assertEqual(admission[0]["reason"], "external policy")

        metrics = probe.evaluate_recall_turn(
            turn=3,
            mode="ask_no_response",
            expected_words=[],
            unexpected_words=[],
            activation=activation,
            gated=gated,
            prompt="",
            response_text="",
            response_skipped=True,
            stage_diagnostics=events,
        )
        self.assertEqual(
            metrics["stage_counts"]["external_admission_dropped"], 1
        )
        self.assertEqual(
            metrics["dropped_reason_counts"]["external policy"], 1
        )

    def test_gate_diagnostics_preserve_cap_before_score_and_fatigue_order(self):
        recorder = DiagnosticRecorder()
        activation = probe.ActivationResult(
            input_words=[
                ExtractedWord("alpha", 1.0),
                ExtractedWord("beta", 1.0),
            ],
            activated_words=[
                probe.ActivatedWord("alpha", 1.0, 0, ["thread-1"], ["alpha"]),
                probe.ActivatedWord("beta", 0.9, 0, ["thread-1"], ["beta"]),
            ],
            activated_threads=[
                probe.ActivatedThread(
                    thread_id="thread-1",
                    score=1.0,
                    base_score=1.0,
                    common_bonus=0.0,
                    words=["alpha", "beta"],
                    matched_words=["alpha", "beta"],
                    activated_by=["alpha", "beta"],
                    date="2026-01-01",
                    canonical_key="alpha|beta",
                )
            ],
            traces=[],
        )

        gate = probe.ActivationGate(
            max_prompt_threads=2,
            max_core_words_per_thread=2,
            max_prompt_words=1,
            min_thread_score=0.05,
            min_word_score=0.05,
            diagnostics=recorder,
        )
        gated = gate.gate(activation)

        self.assertEqual([word.word for word in gated.words], ["alpha"])
        events = recorder.to_jsonable()
        stage_events = [
            event for event in events
            if event["stage"] in {
                "POST_SCORE_SELECTION",
                "POST_FATIGUE",
                "CAP_DROPPED",
            }
        ]
        self.assertEqual(
            [(event["stage"], event["identifier"]) for event in stage_events],
            [
                ("POST_SCORE_SELECTION", "alpha"),
                ("POST_FATIGUE", "alpha"),
                ("CAP_DROPPED", "beta"),
            ],
        )
        self.assertEqual(stage_events[-1]["reason"],
                         "max_prompt_words reached before per-word gate/fatigue checks")

        metrics = probe.evaluate_recall_turn(
            turn=1,
            mode="ask_no_response",
            expected_words=[],
            unexpected_words=[],
            activation=activation,
            gated=gated,
            prompt="",
            response_text="",
            response_skipped=True,
            stage_diagnostics=events,
        )
        self.assertEqual(metrics["stage_counts"]["raw_activation"], 2)
        self.assertEqual(metrics["stage_counts"]["post_score_selection"], 1)
        self.assertEqual(metrics["stage_counts"]["post_fatigue"], 1)
        self.assertEqual(metrics["stage_counts"]["cap_dropped"], 1)
        self.assertEqual(metrics["stage_counts"]["working_memory"], 1)
        self.assertEqual(
            metrics["dropped_reason_counts"][
                "max_prompt_words reached before per-word gate/fatigue checks"
            ],
            1,
        )


if __name__ == "__main__":
    unittest.main()
