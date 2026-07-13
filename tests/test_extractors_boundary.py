import argparse
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from threaded_concept_memory_probe import WordExtractor  # noqa: E402
from trace_recall.extractors import ExtractedWord, TraceExtractor, create_extractor, fallback_extract_words  # noqa: E402
from trace_recall.extractors.fallback import FallbackTraceExtractor  # noqa: E402
from trace_recall.extractors.llm import LLMTraceExtractor  # noqa: E402
from trace_recall.extractors.local_rule import LocalRuleTraceExtractor  # noqa: E402

REPRESENTATIVE_CASES = [
    "私の名前はのりこです。",
    "僕の名前はみつきです。",
    "僕はチーズケーキが好きです。",
    "来週の金曜日が誕生日です。",
    "今度一緒に映画を見に行こう。",
    "昨日は仕事で疲れた。",
]

EXPECTED_FALLBACK = {
    "私の名前はのりこです。": [("私", 0.8), ("名前", 0.8), ("のりこ", 0.8)],
    "僕の名前はみつきです。": [("僕", 0.8), ("名前", 0.8), ("みつき", 0.8)],
    "僕はチーズケーキが好きです。": [("チーズケーキ", 1.2), ("好き", 1.0), ("僕", 0.8)],
    "来週の金曜日が誕生日です。": [("誕生日", 1.0), ("来週", 0.8), ("金曜日", 0.8)],
    "今度一緒に映画を見に行こう。": [("映画", 1.0), ("今度一緒", 0.8), ("見", 0.8), ("行こう", 0.8)],
    "昨日は仕事で疲れた。": [("仕事", 0.8), ("疲れた", 0.8)],
}

LLM_RESPONSE = {
    "私の名前はのりこです。": [("のりこ", 1.4), ("名前", 1.0)],
    "僕の名前はみつきです。": [("みつき", 1.4), ("名前", 1.0)],
    "僕はチーズケーキが好きです。": [("チーズケーキ", 1.4), ("好き", 1.0)],
    "来週の金曜日が誕生日です。": [("誕生日", 1.4), ("金曜日", 1.1), ("来週", 1.0)],
    "今度一緒に映画を見に行こう。": [("映画", 1.3), ("見に行く", 1.0), ("今度", 0.9)],
    "昨日は仕事で疲れた。": [("仕事", 1.2), ("疲れた", 1.1), ("昨日", 0.9)],
}


def pairs(words):
    return [(word.word, word.weight) for word in words]


def json_words(items):
    body = ",".join(f'{{"word":"{word}","weight":{weight}}}' for word, weight in items)
    return f'{{"words":[{body}]}}'


class ExtractorBoundaryTests(unittest.TestCase):
    def test_trace_extractor_protocol_accepts_extract_implementations(self):
        extractor: TraceExtractor = FallbackTraceExtractor()
        self.assertTrue(hasattr(extractor, "extract"))
        self.assertIsInstance(extractor.extract("映画"), list)

    def test_factory_creates_requested_extractors(self):
        common = dict(base_url="http://example.test/v1", api_key="", model="test-model", extractor_model="", timeout=12.0, debug_extractor=False)
        fallback = create_extractor(argparse.Namespace(extractor="fallback", **common))
        llm = create_extractor(argparse.Namespace(extractor="llm", **common), chat_client=lambda **kwargs: '{"words":[]}')
        local_rule = create_extractor(argparse.Namespace(extractor="local-rule", **common))

        self.assertIsInstance(fallback, FallbackTraceExtractor)
        self.assertIsInstance(llm, LLMTraceExtractor)
        self.assertIsInstance(local_rule, LocalRuleTraceExtractor)

    def test_fallback_representative_outputs_are_fixed(self):
        for text in REPRESENTATIVE_CASES:
            with self.subTest(text=text):
                self.assertEqual(pairs(fallback_extract_words(text)), EXPECTED_FALLBACK[text])

    def test_llm_representative_outputs_are_fixed(self):
        extractor = WordExtractor("http://example.test/v1", model="test-model")
        for text in REPRESENTATIVE_CASES:
            with self.subTest(text=text):
                with patch("threaded_concept_memory_probe.call_openai_compatible_chat", return_value=json_words(LLM_RESPONSE[text])):
                    self.assertEqual(pairs(extractor.extract(text)), LLM_RESPONSE[text])

    def test_llm_falls_back_to_representative_fallback_outputs(self):
        extractor = WordExtractor("http://example.test/v1", model="test-model")
        for text in REPRESENTATIVE_CASES:
            with self.subTest(text=text):
                with patch("threaded_concept_memory_probe.call_openai_compatible_chat", side_effect=RuntimeError("boom")):
                    self.assertEqual(pairs(extractor.extract(text)), EXPECTED_FALLBACK[text])


if __name__ == "__main__":
    unittest.main()
