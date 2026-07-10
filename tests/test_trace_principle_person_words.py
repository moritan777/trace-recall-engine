import tempfile
import unittest
from pathlib import Path
import io
import sys
from contextlib import redirect_stderr
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from threaded_concept_memory_probe import (  # noqa: E402
    ActivationEngine,
    ExtractedWord,
    ThreadedConceptMemoryStore,
    WordExtractor,
    fallback_extract_words,
)


class TracePrinciplePersonWordTests(unittest.TestCase):
    def make_store(self):
        tmp = tempfile.TemporaryDirectory()
        store = ThreadedConceptMemoryStore(str(Path(tmp.name) / "memory.db"))
        self.addCleanup(store.close)
        self.addCleanup(tmp.cleanup)
        return store

    def words(self, *items):
        return [ExtractedWord(word, weight) for word, weight in items]

    def activated_word_names(self, result):
        return [word.word for word in result.activated_words]

    def test_name_seed_is_not_recalled_by_unrelated_input(self):
        store = self.make_store()
        store.create_thread(self.words(("みつき", 1.0)), source_text="みつき")
        store.create_thread(self.words(("映画", 1.0), ("ポップコーン", 1.0)), source_text="映画とポップコーン")

        result = ActivationEngine(store).activate(self.words(("映画", 1.0)), top_words=10, top_threads=10)

        self.assertNotIn("みつき", self.activated_word_names(result))

    def test_name_is_recalled_only_when_input_contains_name_by_normal_rules(self):
        store = self.make_store()
        store.create_thread(self.words(("みつき", 1.0), ("チーズケーキ", 1.0)), source_text="みつきはチーズケーキが好き")
        store.create_thread(self.words(("映画", 1.0), ("ポップコーン", 1.0)), source_text="映画とポップコーン")

        without_name = ActivationEngine(store).activate(self.words(("映画", 1.0)), top_words=10, top_threads=10)
        with_name = ActivationEngine(store).activate(self.words(("みつき", 1.0)), top_words=10, top_threads=10)

        self.assertNotIn("みつき", self.activated_word_names(without_name))
        self.assertIn("みつき", self.activated_word_names(with_name))
        self.assertIn("チーズケーキ", self.activated_word_names(with_name))

    def test_multiple_people_preferences_run_without_person_boost(self):
        store = self.make_store()
        store.create_thread(self.words(("みつき", 1.0), ("チーズケーキ", 1.0), ("好き", 1.0)), source_text="みつきはチーズケーキが好き")
        store.create_thread(self.words(("のりこ", 1.0), ("紅茶", 1.0), ("好き", 1.0)), source_text="のりこは紅茶が好き")

        result = ActivationEngine(store).activate(self.words(("みつき", 1.0), ("好き", 1.0)), top_words=10, top_threads=10)
        top_thread = result.activated_threads[0]

        self.assertIn("みつき", top_thread.words)
        self.assertIn("チーズケーキ", top_thread.words)
        self.assertNotIn("のりこ", top_thread.words)
        self.assertNotIn("紅茶", top_thread.words)

    def test_fallback_extraction_keeps_person_words_on_normal_route(self):
        extracted = {word.word: word.weight for word in fallback_extract_words("ユーザーはチーズケーキが好き")}

        self.assertIn("ユーザー", extracted)
        self.assertIn("チーズケーキ", extracted)
        self.assertEqual(extracted["ユーザー"], 0.8)

    def test_fallback_extraction_preserves_word_initial_no(self):
        assistant_name = {word.word for word in fallback_extract_words("私の名前はのりこです。")}
        user_name = {word.word for word in fallback_extract_words("僕の名前はみつきです。")}
        assistant_preference = {word.word for word in fallback_extract_words("のりこは紅茶が好きです。")}

        self.assertIn("名前", assistant_name)
        self.assertIn("のりこ", assistant_name)
        self.assertNotIn("りこ", assistant_name)
        self.assertIn("名前", user_name)
        self.assertIn("みつき", user_name)
        self.assertIn("のりこ", assistant_preference)
        self.assertIn("紅茶", assistant_preference)
        self.assertIn("好き", assistant_preference)

    def test_llm_extractor_system_prompt_mentions_relational_bridge_words(self):
        extractor = WordExtractor("http://example.test/v1", model="test-model")
        raw_response = '{"words":[{"word":"名前","weight":1.0},{"word":"のりこ","weight":1.4}]}'

        with patch("threaded_concept_memory_probe.call_openai_compatible_chat", return_value=raw_response) as mock_chat:
            extractor.extract("私の名前はのりこです。")

        messages = mock_chat.call_args.kwargs["messages"]
        system_prompt = messages[0]["content"]
        self.assertIn("relational bridge words", system_prompt)
        self.assertIn("名前", system_prompt)
        self.assertIn("Do not return only the most specific proper noun", system_prompt)
        self.assertIn("from an utterance", system_prompt)
        self.assertNotIn("from a user utterance", system_prompt)

    def test_llm_extractor_keeps_name_bridge_and_specific_name_from_raw_response(self):
        extractor = WordExtractor("http://example.test/v1", model="test-model")
        raw_response = '{"words":[{"word":"名前","weight":1.0},{"word":"のりこ","weight":1.4}]}'

        with patch("threaded_concept_memory_probe.call_openai_compatible_chat", return_value=raw_response):
            words = extractor.extract("私の名前はのりこです。")

        extracted = {word.word: word.weight for word in words}
        self.assertEqual(extracted["名前"], 1.0)
        self.assertEqual(extracted["のりこ"], 1.4)

    def test_llm_extractor_debug_shows_name_survives_python_filter(self):
        extractor = WordExtractor("http://example.test/v1", model="test-model", debug=True)
        raw_response = '{"words":[{"word":"私","weight":0.8},{"word":"名前","weight":1.0},{"word":"のりこ","weight":1.0}]}'
        stderr = io.StringIO()

        with patch("threaded_concept_memory_probe.call_openai_compatible_chat", return_value=raw_response):
            with redirect_stderr(stderr):
                words = extractor.extract("私の名前はのりこです。")

        debug_output = stderr.getvalue()
        extracted = {word.word for word in words}
        self.assertIn("名前", extracted)
        self.assertIn("のりこ", extracted)
        self.assertIn("[LLM Extractor Debug] system prompt BEGIN", debug_output)
        self.assertIn("Input:\n私の名前はのりこです。\n\nReturn JSON only.", debug_output)
        self.assertIn(raw_response, debug_output)
        self.assertIn('"word": "名前"', debug_output)
        self.assertIn("contains 名前 after python filter=True", debug_output)


if __name__ == "__main__":
    unittest.main()
