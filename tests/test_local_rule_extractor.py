import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trace_recall.extractors.local_rule import LocalRuleTraceExtractor  # noqa: E402


def words(text: str) -> set[str]:
    return {item.word for item in LocalRuleTraceExtractor().extract(text)}


class LocalRuleTraceExtractorTests(unittest.TestCase):
    def assertContainsAll(self, text: str, expected: set[str]) -> None:
        extracted = words(text)
        self.assertTrue(expected <= extracted, f"missing {expected - extracted}; extracted={sorted(extracted)}")

    def test_name_keeps_initial_no(self):
        self.assertContainsAll("私の名前はのりこです。", {"私", "名前", "のりこ"})
        self.assertNotIn("りこ", words("私の名前はのりこです。"))

    def test_compound_preference(self):
        self.assertContainsAll("僕はチーズケーキが好きです。", {"チーズケーキ", "好き"})

    def test_time_bridge(self):
        self.assertContainsAll("来週の金曜日が誕生日です。", {"来週", "金曜日", "誕生日"})

    def test_future_plan_keeps_compound_action(self):
        extracted = words("今度一緒に映画を見に行こう。")
        self.assertTrue({"今度", "映画"} <= extracted)
        self.assertIn("見に行く", extracted)

    def test_boundary_expression(self):
        self.assertContainsAll("元カノの話はやめて。", {"元カノ", "話", "やめて"})

    def test_conversation_bridge(self):
        self.assertContainsAll("昨日話した映画。", {"昨日", "話した", "映画"})

    def test_negation_keeps_both_sides(self):
        self.assertContainsAll("紅茶じゃなくてコーヒーが飲みたい。", {"紅茶", "コーヒー", "飲みたい"})

    def test_third_person_is_not_canonicalized(self):
        self.assertContainsAll("友達のたけしは映画が好きです。", {"友達", "たけし", "映画", "好き"})
        self.assertFalse({"@user", "@assistant"} & words("友達のたけしは映画が好きです。"))


if __name__ == "__main__":
    unittest.main()


class _FakeTraceVocabulary:
    def __init__(self, words):
        self.words = words
        self.calls = 0

    def get_trace_vocabulary(self):
        self.calls += 1
        return list(self.words)


class DynamicTraceDictionaryTests(unittest.TestCase):
    def test_trace_dictionary_longest_match_prefix_conflict(self):
        provider = _FakeTraceVocabulary([
            ("AI", 1.0),
            ("AIKanojyo", 1.2),
            ("AIKanojyo Project", 1.5),
        ])
        extractor = LocalRuleTraceExtractor(trace_vocabulary=provider)
        extracted = {item.word for item in extractor.extract("AIKanojyo Projectを作る")}
        self.assertIn("AIKanojyo Project", extracted)
        self.assertNotIn("AIKanojyo", extracted)
        self.assertNotIn("AI", extracted)
        self.assertTrue(extractor.last_diagnostics["longest_match_success"])

    def test_trace_dictionary_overlap_keeps_only_longest_span(self):
        provider = _FakeTraceVocabulary([("長期", 1.0), ("長期記憶", 1.3)])
        extractor = LocalRuleTraceExtractor(trace_vocabulary=provider)
        extracted = {item.word for item in extractor.extract("長期記憶を実装した")}
        self.assertIn("長期記憶", extracted)
        self.assertNotIn("長期", extracted)

    def test_unregistered_words_continue_to_local_rules(self):
        extractor = LocalRuleTraceExtractor(trace_vocabulary=_FakeTraceVocabulary([]))
        extracted = {item.word for item in extractor.extract("僕はチーズケーキが好きです。")}
        self.assertTrue({"チーズケーキ", "好き"} <= extracted)
