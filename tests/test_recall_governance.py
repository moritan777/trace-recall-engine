import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from threaded_concept_memory_probe import (  # noqa: E402
    ActivatedThread, ActivatedWord, ActivationGate, ActivationResult, WordNode,
)
from trace_recall.diagnostics import DiagnosticRecorder, RecallStage  # noqa: E402
from trace_recall.extractors import ExtractedWord  # noqa: E402
from trace_recall.governance import (  # noqa: E402
    AdmissionAction, AdmissionDecision, ConflictState, RecallExpectation,
    RecallOutcome, evaluate_expectations, parse_expectation,
)
from trace_recall.offline import compare_lateral_inhibition  # noqa: E402


class FakeStore:
    def __init__(self, fatigue=None):
        self.fatigue = fatigue or {}

    def get_fatigue_prompt(self, word, recent_turns):
        return self.fatigue.get(word, 0)

    def get_fatigue_response(self, word, recent_turns):
        return 0

    def get_word_by_text(self, word):
        return WordNode(word, word, 1.25, 1.0, 7, "2020", "2020")


def activation(input_words=("topic",)):
    words = [
        ActivatedWord("topic", 1.0, 0, ["thread-1"], ["input:topic"]),
        ActivatedWord("memory", 0.6, 2, ["thread-1"], ["thread:thread-1"]),
    ]
    thread = ActivatedThread("thread-1", 1.2, 1.0, 0.2, ["topic", "memory"], ["topic"], ["word:topic"], "2020")
    return ActivationResult([ExtractedWord(w, 1.0) for w in input_words], words, [thread], [])


class RecallGovernanceTests(unittest.TestCase):
    def test_all_expectation_labels_parse_and_evaluate(self):
        for label in RecallExpectation:
            self.assertIs(parse_expectation(label.value.lower()), label)
        result = evaluate_expectations(
            {"a": "SHOULD_RECALL", "b": "MAY_RECALL", "c": "SHOULD_NOT_RECALL", "d": "MUST_NOT_SPEAK"},
            {"a", "d"}, set(),
        )
        self.assertTrue(result["passed"])

    def test_conflicted_and_superseded_remain_distinct_metadata(self):
        self.assertNotEqual(ConflictState.SUPERSEDED, ConflictState.CONFLICTED)
        self.assertEqual(ConflictState("SUPERSEDED").value, "SUPERSEDED")

    def test_hook_can_abstain_and_records_reason(self):
        recorder = DiagnosticRecorder()

        def suppress(candidate, context):
            return AdmissionDecision(AdmissionAction.SUPPRESS, "external test policy")

        gated = ActivationGate(store=FakeStore(), admission_hook=suppress, diagnostics=recorder).gate(activation())
        self.assertEqual(gated.words, [])
        self.assertEqual(gated.threads, [])
        self.assertEqual(gated.outcome, RecallOutcome.CANDIDATES_SUPPRESSED.value)
        suppressed = [e for e in recorder.events if e.stage is RecallStage.EXTERNAL_ADMISSION]
        self.assertTrue(suppressed)
        self.assertTrue(all(e.reason == "external test policy" for e in suppressed))

    def test_no_hook_is_compatible_and_diagnostics_are_observational(self):
        plain = ActivationGate(store=FakeStore()).gate(activation())
        recorder = DiagnosticRecorder()
        observed = ActivationGate(store=FakeStore(), diagnostics=recorder).gate(activation())
        self.assertEqual(plain, observed)
        stages = [event.stage for event in recorder.events]
        self.assertLess(stages.index(RecallStage.RAW_ACTIVATION), stages.index(RecallStage.ACTIVATION_GATE))
        self.assertLess(stages.index(RecallStage.ACTIVATION_GATE), stages.index(RecallStage.RECALL_SELECTION))
        self.assertLess(stages.index(RecallStage.RECALL_SELECTION), stages.index(RecallStage.WORKING_MEMORY))
        self.assertTrue(all(event.reason for event in recorder.events))
        raw = next(e for e in recorder.events if e.stage is RecallStage.RAW_ACTIVATION)
        self.assertEqual(raw.raw_frequency, 7)
        self.assertAlmostEqual(raw.reinforcement_contribution, 0.25)

    def test_fatigue_suppresses_association_but_direct_user_reentry_overrides(self):
        store = FakeStore({"topic": 3, "memory": 3})
        other = ActivationGate(store=store, fatigue_threshold=3).gate(activation(("other",)))
        self.assertNotIn("topic", [word.word for word in other.words])
        self.assertEqual(other.topic_reentry_words, [])

        reentry = ActivationGate(store=store, fatigue_threshold=3).gate(activation(("topic",)))
        self.assertIn("topic", [word.word for word in reentry.words])
        self.assertEqual(reentry.topic_reentry_words, ["topic"])
        self.assertNotIn("memory", reentry.topic_reentry_words)

    def test_lateral_inhibition_is_an_offline_metric_only(self):
        result = compare_lateral_inhibition([("strong", 1.0), ("weak", 0.1)], {"strong"}, {"weak"})
        self.assertEqual(result["selected"], ["strong"])
        self.assertEqual(result["unexpected_hit_reduction"], 1)
        self.assertEqual(result["counterexample_count"], 0)


if __name__ == "__main__":
    unittest.main()
