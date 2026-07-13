import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trace_recall.extractors.japanese_trace_tokenizer import JapaneseTraceTokenizer  # noqa: E402
from trace_recall.extractors.local_rule import LocalRuleTraceExtractor  # noqa: E402


@dataclass(frozen=True)
class Span:
    start: int
    end: int


class JapaneseTraceTokenizerTests(unittest.TestCase):
    def tokens(self, text, spans=None):
        return [t.text for t in JapaneseTraceTokenizer().tokenize(text, spans)]

    def test_short_utterance_is_not_over_split(self):
        self.assertEqual(self.tokens("映画"), ["映画"])

    def test_particle_boundaries_split_long_phrase(self):
        self.assertTrue({"映画", "観にいこ"} <= set(self.tokens("映画観にいこ")))

    def test_long_sentence_keeps_trace_phrases(self):
        result = set(self.tokens("この前駅前で見つけた新しいカフェのチーズケーキが思ったより美味しかった"))
        self.assertTrue({"この前駅前", "見つけた新しいカフェ", "チーズケーキ", "思ったより美味しかった"} <= result)

    def test_connective_boundaries(self):
        self.assertTrue({"映画", "明日行こう"} <= set(self.tokens("映画だけど明日行こう")))

    def test_protected_span_is_not_broken(self):
        text = "ChatGPT PlusでMemory Recallを試す"
        spans = [Span(text.index("ChatGPT Plus"), text.index("ChatGPT Plus") + len("ChatGPT Plus"))]
        result = self.tokens(text, spans)
        self.assertNotIn("ChatGPT", result)
        self.assertNotIn("Plus", result)

    def test_alternate_spans_are_generated_without_replacing_primary(self):
        tokenizer = JapaneseTraceTokenizer()
        primary = [t.text for t in tokenizer.tokenize("俺の名前、みつきな")]
        alternate = set(tokenizer.last_diagnostics["tokenizer_alternate_spans"])
        self.assertIn("みつきな", primary)
        self.assertIn("みつき", alternate)

    def test_alternate_spans_split_mixed_and_future_plan_chunks(self):
        tokenizer = JapaneseTraceTokenizer()
        tokenizer.tokenize("SF映画に目がない")
        self.assertTrue({"SF映画", "映画"} <= set(tokenizer.last_diagnostics["tokenizer_alternate_spans"]))
        tokenizer.tokenize("近いうち映画観にいこ")
        self.assertTrue({"近いうち", "映画", "観にいこ"} <= set(tokenizer.last_diagnostics["tokenizer_alternate_spans"]))

    def test_extractor_exposes_tokenizer_diagnostics(self):
        extractor = LocalRuleTraceExtractor()
        words = {item.word for item in extractor.extract("今度映画を観にいこ")}
        self.assertTrue({"今度", "映画", "観にいこ"} <= words)
        self.assertIn("tokenizer_candidate_count", extractor.last_diagnostics)
        self.assertIn("tokenizer_split_count", extractor.last_diagnostics)


if __name__ == "__main__":
    unittest.main()
