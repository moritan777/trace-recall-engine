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

    def _cap_case(self):
        recorder = DiagnosticRecorder()
        activation = probe.ActivationResult(
            input_words=[ExtractedWord("alpha", 1.0), ExtractedWord("beta", 1.0)],
            activated_words=[
                probe.ActivatedWord("alpha", 1.0, 0, ["thread-1"], ["alpha"]),
                probe.ActivatedWord("beta", 0.9, 0, ["thread-1"], ["beta"]),
            ],
            activated_threads=[
                probe.ActivatedThread(
                    thread_id="thread-1", score=1.0, base_score=1.0, common_bonus=0.0,
                    words=["alpha", "beta"], matched_words=["alpha", "beta"],
                    activated_by=["alpha", "beta"], date="2026-01-01", canonical_key="alpha|beta",
                )
            ],
            traces=[],
        )
        gate = probe.ActivationGate(
            max_prompt_threads=2, max_core_words_per_thread=2, max_prompt_words=1,
            min_thread_score=0.05, min_word_score=0.05, diagnostics=recorder,
        )
        gated = gate.gate(activation)
        return activation, gated, recorder.to_jsonable()

    def test_expected_stage_trace_locates_loss_stage(self):
        activation, gated, events = self._cap_case()
        metrics = probe.evaluate_recall_turn(
            turn=1, mode="ask_no_response",
            expected_words=["alpha", "beta", "gamma", "delta"], unexpected_words=[],
            activation=activation, gated=gated, prompt="context: alpha",
            response_text="", response_skipped=True, stage_diagnostics=events,
            stored_expected_words={"alpha", "beta", "gamma"},
        )
        trace = metrics["expected_stage_trace"]
        loss = {w: info["loss_stage"] for w, info in trace["per_word"].items()}
        self.assertEqual(loss, {
            "alpha": "survived",      # reached prompt; response not measured
            "beta": "cap",            # activated, dropped by prompt-word cap
            "gamma": "raw_activation",  # stored but never activated
            "delta": "stored",        # never stored
        })
        self.assertIsNone(trace["per_word"]["alpha"]["stages"]["response"])
        self.assertFalse(trace["per_word"]["beta"]["stages"]["working_memory"])
        self.assertEqual(trace["survival_counts"]["raw_activation"], 2)
        self.assertEqual(trace["measured_counts"]["response"], 0)

    def test_expected_stage_trace_reports_response_when_enabled(self):
        activation, gated, events = self._cap_case()
        metrics = probe.evaluate_recall_turn(
            turn=1, mode="ask", expected_words=["alpha"], unexpected_words=[],
            activation=activation, gated=gated, prompt="context: alpha",
            response_text="nothing relevant", response_skipped=False, stage_diagnostics=events,
        )
        info = metrics["expected_stage_trace"]["per_word"]["alpha"]
        self.assertIsNone(info["stages"]["stored"])  # no store lookup given
        self.assertEqual(info["loss_stage"], "response")

    def test_expected_stage_trace_flows_into_csv_summary(self):
        activation, gated, events = self._cap_case()
        metrics = probe.evaluate_recall_turn(
            turn=1, mode="ask_no_response", expected_words=["alpha", "beta"], unexpected_words=[],
            activation=activation, gated=gated, prompt="alpha", response_text="",
            response_skipped=True, stage_diagnostics=events,
        )
        row = probe.flatten_eval_metrics({"metrics": metrics})
        self.assertEqual(row["expected_total"], 2)
        self.assertEqual(row["expected_survived_cap"], 1)
        summary = "\n".join(probe.build_eval_report_summary([row]))
        self.assertIn("## Expected Word Stage Survival", summary)
        self.assertIn('"cap": 1', summary)


if __name__ == "__main__":
    unittest.main()
