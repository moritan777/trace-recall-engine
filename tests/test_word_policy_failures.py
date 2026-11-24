import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trace_recall.extractors.base import (  # noqa: E402
    ACTION_DROPPED,
    ACTION_KEPT_SURFACE,
    CANONICALIZE_EMPTY,
    CANONICALIZE_ERROR,
    POLICY_REJECTED,
    SHOULD_KEEP_ERROR,
    ExtractedWord,
    finalize_extracted_words,
)


class _Policy:
    """Configurable policy for failure-path tests."""

    def __init__(self, reject=(), keep_raises=(), canon_raises=(), canon_empty=(), canon_map=None):
        self.reject = set(reject)
        self.keep_raises = set(keep_raises)
        self.canon_raises = set(canon_raises)
        self.canon_empty = set(canon_empty)
        self.canon_map = dict(canon_map or {})

    def should_keep(self, word):
        if word in self.keep_raises:
            raise RuntimeError("keep boom")
        return word not in self.reject

    def canonicalize(self, word):
        if word in self.canon_raises:
            raise ValueError("unknown stem")
        if word in self.canon_empty:
            return ""
        return self.canon_map.get(word, word)


def _words(*items):
    return [ExtractedWord(w, 1.0) for w in items]


def _surfaces(result):
    return sorted(item.word for item in result)


class WordPolicyFailureTests(unittest.TestCase):
    def test_identity_policy_records_nothing(self):
        events = []
        result = finalize_extracted_words(_words("a", "b"), events=events)
        self.assertEqual(_surfaces(result), ["a", "b"])
        self.assertEqual(events, [])

    def test_events_argument_is_optional(self):
        result = finalize_extracted_words(_words("az", "ház"), policy=_Policy(reject={"az"}))
        self.assertEqual(_surfaces(result), ["ház"])

    def test_rejection_drops_and_is_recorded(self):
        events = []
        result = finalize_extracted_words(_words("az", "ház"), policy=_Policy(reject={"az"}), events=events)
        self.assertEqual(_surfaces(result), ["ház"])
        self.assertEqual([(e.surface, e.failure_type, e.action) for e in events],
                         [("az", POLICY_REJECTED, ACTION_DROPPED)])

    def test_should_keep_error_keeps_candidate(self):
        events = []
        result = finalize_extracted_words(_words("x"), policy=_Policy(keep_raises={"x"}), events=events)
        self.assertEqual(_surfaces(result), ["x"])
        self.assertEqual(events[0].failure_type, SHOULD_KEEP_ERROR)
        self.assertEqual(events[0].action, ACTION_KEPT_SURFACE)
        self.assertIn("keep boom", events[0].detail)

    def test_canonicalize_error_falls_back_to_surface(self):
        events = []
        result = finalize_extracted_words(_words("házban"), policy=_Policy(canon_raises={"házban"}), events=events)
        self.assertEqual(_surfaces(result), ["házban"])
        self.assertIsNone(result[0].canonical_word)
        self.assertEqual(events[0].failure_type, CANONICALIZE_ERROR)
        self.assertEqual(events[0].action, ACTION_KEPT_SURFACE)
        self.assertIn("ValueError", events[0].detail)

    def test_canonicalize_empty_falls_back_to_surface(self):
        events = []
        result = finalize_extracted_words(_words("y"), policy=_Policy(canon_empty={"y"}), events=events)
        self.assertEqual(_surfaces(result), ["y"])
        self.assertEqual(events[0].failure_type, CANONICALIZE_EMPTY)
        self.assertEqual(events[0].action, ACTION_KEPT_SURFACE)

    def test_non_string_canonical_is_an_error_not_a_crash(self):
        class Bad(_Policy):
            def canonicalize(self, word):
                return None

        events = []
        result = finalize_extracted_words(_words("z"), policy=Bad(), events=events)
        self.assertEqual(_surfaces(result), ["z"])
        self.assertEqual(events[0].failure_type, CANONICALIZE_ERROR)

    def test_failure_types_are_distinguishable_in_one_field(self):
        events = []
        policy = _Policy(reject={"r"}, keep_raises={"k"}, canon_raises={"c"}, canon_empty={"e"})
        finalize_extracted_words(_words("r", "k", "c", "e", "ok"), policy=policy, events=events)
        self.assertEqual(
            {e.surface: (e.failure_type, e.action) for e in events},
            {
                "r": (POLICY_REJECTED, ACTION_DROPPED),
                "k": (SHOULD_KEEP_ERROR, ACTION_KEPT_SURFACE),
                "c": (CANONICALIZE_ERROR, ACTION_KEPT_SURFACE),
                "e": (CANONICALIZE_EMPTY, ACTION_KEPT_SURFACE),
            },
        )

    def test_successful_canonicalization_still_dedupes(self):
        events = []
        policy = _Policy(canon_map={"házban": "ház", "házat": "ház"})
        result = finalize_extracted_words(
            [ExtractedWord("házban", 0.8), ExtractedWord("házat", 1.2)], policy=policy, events=events
        )
        self.assertEqual([(r.word, r.canonical_word) for r in result], [("házat", "ház")])
        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
