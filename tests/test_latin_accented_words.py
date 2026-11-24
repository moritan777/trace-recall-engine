import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trace_recall.extractors.fallback import fallback_extract_words  # noqa: E402


def fallback_words(text: str) -> list[str]:
    return [item.word for item in fallback_extract_words(text)]


class FallbackAccentedLatinTests(unittest.TestCase):
    def test_accented_letter_does_not_split_a_word(self):
        words = fallback_words("A házakban laktunk")
        self.assertIn("házakban", words)
        self.assertIn("laktunk", words)
        self.assertNotIn("h", words)
        self.assertNotIn("zakban", words)

    def test_double_acute_letters_are_word_characters(self):
        words = fallback_words("Győr szőlő")
        self.assertIn("Győr", words)
        self.assertIn("szőlő", words)

    def test_decomposed_accent_is_composed_before_chunking(self):
        self.assertEqual(fallback_words("ha\u0301z"), ["ház"])

    def test_multiplication_sign_still_separates(self):
        self.assertEqual(sorted(fallback_words("5×3")), ["3", "5"])

    def test_japanese_and_ascii_behavior_is_unchanged(self):
        self.assertEqual(
            sorted(fallback_words("みつきはチーズケーキが好き")),
            sorted(["チーズケーキ", "好き", "みつき"]),
        )
        self.assertIn("ChatGPT", fallback_words("ChatGPTが好き"))


class LocalRuleAccentedLatinTests(unittest.TestCase):
    def test_local_rule_does_not_cut_accented_word(self):
        from trace_recall.extractors.local_rule import LocalRuleTraceExtractor

        words = [item.word for item in LocalRuleTraceExtractor().extract("A házakban laktunk")]
        self.assertNotIn("h", words)
        self.assertNotIn("A h", words)
        for word in words:
            if "zakban" in word:
                self.assertIn("házakban", word)


if __name__ == "__main__":
    unittest.main()
