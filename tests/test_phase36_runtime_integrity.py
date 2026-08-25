import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from threaded_concept_memory_probe import (
    ActivatedWord, ActivationResult, ExtractedWord, GatedContext, GatedWord,
    ResponseGenerator, evaluate_recall_turn, fallback_generate_response,
)
from trace_recall.extractors.llm import LLMTraceExtractor


class Phase36RuntimeIntegrityTests(unittest.TestCase):
    def activation(self):
        return ActivationResult(
            [ExtractedWord("A", 1.0)],
            [ActivatedWord(x, 1.0, 0, [], []) for x in ["A", "B", "C"]], [], [],
        )

    def test_gated_fallback_never_revives_suppressed_words(self):
        gated = GatedContext([], [GatedWord("A", 1, 0, "core", "")], [
            GatedWord("B", 1, 0, "suppressed", ""), GatedWord("C", 1, 0, "suppressed", "")], "")
        text = fallback_generate_response("question", self.activation(), gated)
        self.assertIn("A", text)
        self.assertNotIn("B", text)
        self.assertNotIn("C", text)

    def test_empty_gated_fallback_abstains(self):
        text = fallback_generate_response("question", self.activation(), GatedContext([], [], [], ""))
        self.assertIn("思い出せない", text)
        self.assertNotIn("A", text)

    def test_recall_speaking_and_suppression_are_separate(self):
        gated = GatedContext([], [GatedWord("A", 1, 0, "core", "")], [GatedWord("B", 1, 0, "x", "")], "")
        result = evaluate_recall_turn(1, "ask", ["A"], ["B"], self.activation(), gated, "prompt", "B")
        self.assertEqual(result["recall_expected_hit_count"], 1)
        self.assertEqual(result["recall_unexpected_hit_count"], 0)
        self.assertEqual(result["spoken_expected_hit_count"], 0)
        self.assertEqual(result["spoken_unexpected_hit_count"], 1)
        self.assertEqual(result["spoken_suppressed_count"], 1)
        self.assertEqual((result["expected_hit_count"], result["unexpected_hit_count"]), (1, 1))

    def test_response_timeout_diagnostic_and_prompt_identity(self):
        generator = ResponseGenerator("http://example.test", model="m", timeout_sec=60)
        gated = GatedContext([], [GatedWord("A", 1, 0, "core", "")], [], "")
        with patch("threaded_concept_memory_probe.call_openai_compatible_chat", side_effect=TimeoutError("timed out")) as call:
            generator.generate("q", self.activation(), gated=gated, prompt="EXACT")
        self.assertEqual(call.call_args.kwargs["messages"][1]["content"], "EXACT")
        self.assertEqual(generator.last_prompt, "EXACT")
        self.assertEqual(generator.last_result_metadata["failure_type"], "TIMEOUT")
        self.assertTrue(generator.last_result_metadata["fallback_used"])
        self.assertEqual(generator.last_result_metadata["timeout_sec"], 60)

    def test_extractor_timeout_diagnostic(self):
        extractor = LLMTraceExtractor("http://example.test", model="m", timeout_sec=20,
                                      chat_client=lambda **_: (_ for _ in ()).throw(TimeoutError("timed out")))
        extractor.extract("hello")
        self.assertEqual(extractor.last_result_metadata["actual_extractor"], "fallback")
        self.assertTrue(extractor.last_result_metadata["fallback_used"])
        self.assertEqual(extractor.last_result_metadata["failure_type"], "TIMEOUT")
        self.assertGreaterEqual(extractor.last_result_metadata["elapsed_ms"], 0)


if __name__ == "__main__":
    unittest.main()
