import argparse
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from threaded_concept_memory_probe import ExtractedWord, extract_normalized_words
from trace_recall.extractors.base import (
    IdentityWordPolicy,
    finalize_extracted_words,
)


class CaseFoldPolicy:
    def canonicalize(self, word: str) -> str:
        return word.casefold()

    def should_keep(self, word: str) -> bool:
        return word.casefold() not in {"a", "az"}


class WordPolicyFinalizerTests(unittest.TestCase):
    def test_identity_policy_preserves_existing_surface_words(self):
        words = [
            ExtractedWord("映画", 1.3),
            ExtractedWord(" チーズケーキ。 ", 1.4),
        ]

        result = finalize_extracted_words(words, IdentityWordPolicy())

        self.assertEqual(
            [(item.word, item.weight, item.canonical_word) for item in result],
            [("チーズケーキ", 1.4, None), ("映画", 1.3, None)],
        )

    def test_policy_filters_and_deduplicates_by_canonical_form(self):
        words = [
            ExtractedWord("A", 0.8),
            ExtractedWord("AZ", 0.9),
            ExtractedWord("Házak", 0.7),
            ExtractedWord("HÁZAK", 1.2),
        ]

        result = finalize_extracted_words(words, CaseFoldPolicy())

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].word, "HÁZAK")
        self.assertEqual(result[0].canonical_word, "házak")
        self.assertEqual(result[0].weight, 1.2)

    def test_policy_empty_canonical_form_rejects_candidate(self):
        class EmptyCanonicalPolicy:
            def canonicalize(self, word: str) -> str:
                return ""

            def should_keep(self, word: str) -> bool:
                return True

        self.assertEqual(
            finalize_extracted_words([ExtractedWord("word", 1.0)], EmptyCanonicalPolicy()),
            [],
        )

    def test_policy_errors_are_not_silently_treated_as_success(self):
        class BrokenPolicy:
            def canonicalize(self, word: str) -> str:
                raise RuntimeError("adapter failed")

            def should_keep(self, word: str) -> bool:
                return True

        with self.assertRaisesRegex(RuntimeError, "adapter failed"):
            finalize_extracted_words([ExtractedWord("word", 1.0)], BrokenPolicy())

    def test_runtime_entry_point_uses_the_shared_finalizer(self):
        class StubExtractor:
            def extract(self, text: str) -> list[ExtractedWord]:
                return [ExtractedWord("HÁZAK", 1.0), ExtractedWord("házak", 0.8)]

        args = argparse.Namespace(disable_participant_reference=True)
        result = extract_normalized_words(
            args,
            StubExtractor(),
            "input",
            "user",
            word_policy=CaseFoldPolicy(),
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].word, "HÁZAK")
        self.assertEqual(result[0].canonical_word, "házak")


if __name__ == "__main__":
    unittest.main()
