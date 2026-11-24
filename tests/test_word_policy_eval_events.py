import argparse
import csv
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import threaded_concept_memory_probe as probe  # noqa: E402
from trace_recall.extractors.base import (  # noqa: E402
    MERGED_DUPLICATE,
    ExtractedWord,
    IdentityWordPolicy,
    finalize_extracted_words,
)


class _CaseFold:
    def canonicalize(self, word):
        return word.casefold()

    def should_keep(self, word):
        return word.casefold() != "az"


class _Stub:
    def __init__(self, words):
        self.words = words

    def extract(self, text):
        return [ExtractedWord(w, weight) for w, weight in self.words]


class WordPolicyEvalEventTests(unittest.TestCase):
    def test_merge_of_different_surfaces_is_recorded(self):
        events = []
        result = finalize_extracted_words(
            [ExtractedWord("Házak", 0.7), ExtractedWord("HÁZAK", 1.2)], _CaseFold(), events=events
        )
        self.assertEqual([r.word for r in result], ["HÁZAK"])
        self.assertEqual([(e.surface, e.failure_type) for e in events], [("Házak", MERGED_DUPLICATE)])
        self.assertIn("HÁZAK", events[0].detail)

    def test_identical_surfaces_are_not_recorded_as_merges(self):
        events = []
        finalize_extracted_words([ExtractedWord("映画", 0.8), ExtractedWord("映画", 1.2)], IdentityWordPolicy(), events=events)
        self.assertEqual(events, [])

    def test_merges_are_not_logged_without_events(self):
        with self.assertNoLogs("trace_recall.extractors.base", level="WARNING"):
            finalize_extracted_words([ExtractedWord("Házak", 0.7), ExtractedWord("HÁZAK", 1.2)], _CaseFold())

    def test_resolve_word_policy(self):
        self.assertIsInstance(probe.resolve_word_policy(None), IdentityWordPolicy)
        self.assertIsInstance(probe.resolve_word_policy("identity"), IdentityWordPolicy)
        with self.assertRaises(ValueError):
            probe.resolve_word_policy("klingon")

    def test_extract_normalized_words_collects_events(self):
        args = argparse.Namespace(disable_participant_reference=True, word_policy="identity")
        events = []
        words = probe.extract_normalized_words(
            args, _Stub([("az", 1.0), ("ház", 1.0)]), "x", "user",
            word_policy=_CaseFold(), policy_events=events,
        )
        self.assertEqual([w.word for w in words], ["ház"])
        self.assertEqual([e.failure_type for e in events], ["rejected_by_policy"])

    def test_extract_normalized_words_uses_args_policy_by_default(self):
        args = argparse.Namespace(disable_participant_reference=True)
        words = probe.extract_normalized_words(args, _Stub([("a", 1.0)]), "x", "user")
        self.assertEqual([w.word for w in words], ["a"])

    def test_flatten_and_summary(self):
        row = probe._flatten_word_policy_events([
            {"surface": "az", "failure_type": "rejected_by_policy", "action": "dropped"},
            {"surface": "Házak", "failure_type": "merged_into_canonical", "action": "dropped"},
        ])
        self.assertEqual(row["word_policy_event_count"], 2)
        self.assertEqual(row["word_policy_rejected_by_policy"], 1)
        self.assertEqual(row["word_policy_merged_into_canonical"], 1)
        self.assertEqual(probe._flatten_word_policy_events(None)["word_policy_event_count"], 0)
        summary = "\n".join(probe._word_policy_summary_lines([row]))
        self.assertIn("## Word Policy Events", summary)
        self.assertIn("- rejected_by_policy: 1", summary)
        for name in probe.WORD_POLICY_CSV_FIELDS:
            self.assertIn(name, row)


if __name__ == "__main__":
    unittest.main()
