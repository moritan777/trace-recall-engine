import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import threaded_concept_memory_probe as probe  # noqa: E402
from trace_recall.extractors.base import ExtractedWord, finalize_extracted_words  # noqa: E402
from trace_recall.extractors.fallback import fallback_extract_words  # noqa: E402
from trace_recall.extractors.policies import HungarianWordPolicy  # noqa: E402


def finalize(words):
    events = []
    result = finalize_extracted_words([ExtractedWord(w, 1.0) for w in words], HungarianWordPolicy(), events=events)
    return [r.word for r in result], events


class HungarianWordPolicyTests(unittest.TestCase):
    def test_articles_are_rejected_and_recorded(self):
        words, events = finalize(["A", "házakban", "laktunk"])
        self.assertEqual(sorted(words), ["házakban", "laktunk"])
        self.assertEqual([(e.surface, e.failure_type) for e in events], [("A", "rejected_by_policy")])

    def test_case_variants_share_canonical_form(self):
        result = finalize_extracted_words(
            [ExtractedWord("Házak", 0.7), ExtractedWord("HÁZAK", 1.2)], HungarianWordPolicy()
        )
        self.assertEqual([(r.word, r.canonical_word) for r in result], [("HÁZAK", "házak")])

    def test_no_stemming(self):
        words, _ = finalize(["házban", "ház"])
        self.assertEqual(sorted(words), ["ház", "házban"])

    def test_negation_and_pronouns_are_kept(self):
        words, events = finalize(["nem", "sem", "nincs", "én", "te", "van"])
        self.assertEqual(sorted(words), sorted(["nem", "sem", "nincs", "én", "te", "van"]))
        self.assertEqual(events, [])

    def test_single_latin_letter_dropped_digit_kept(self):
        words, _ = finalize(["h", "5", "ház"])
        self.assertEqual(sorted(words), ["5", "ház"])

    def test_long_words_are_kept(self):
        long_word = "megszentségteleníthetetlenségeskedéseitekért"
        words, _ = finalize([long_word])
        self.assertEqual(words, [long_word])

    def test_decomposed_accent_canonicalizes_to_composed(self):
        self.assertEqual(HungarianWordPolicy().canonicalize("ha\u0301z"), "ház")

    def test_japanese_words_pass_through(self):
        words, events = finalize(["映画", "猫", "みつき"])
        self.assertEqual(sorted(words), sorted(["映画", "猫", "みつき"]))
        self.assertEqual(events, [])

    def test_fallback_pipeline_with_hungarian_policy(self):
        events = []
        result = finalize_extracted_words(fallback_extract_words("A házakban laktunk"), HungarianWordPolicy(), events=events)
        self.assertEqual(sorted(r.word for r in result), ["házakban", "laktunk"])

    def test_registered_for_cli(self):
        self.assertIn("hu", probe.WORD_POLICIES)
        self.assertIsInstance(probe.resolve_word_policy("hu"), HungarianWordPolicy)


if __name__ == "__main__":
    unittest.main()
