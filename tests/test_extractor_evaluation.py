import argparse
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from threaded_concept_memory_probe import (  # noqa: E402
    cmd_eval_extractor,
    evaluate_extractor_scenario,
    load_extractor_scenarios,
)
from trace_recall.extractors.fallback import FallbackTraceExtractor  # noqa: E402


class ExtractorEvaluationTests(unittest.TestCase):
    def test_default_dataset_contains_required_categories_and_cases(self):
        scenarios = load_extractor_scenarios(Path("eval_extractors/extractor_core_ja.jsonl"))
        categories = {item["category"] for item in scenarios}
        required = {
            "Identity",
            "Preference",
            "Date",
            "Emotion",
            "Future Plan",
            "Compound Word",
            "Correction",
            "Negation",
            "Third Person",
            "Relationship",
            "Conversation Bridge",
            "Participant Reference",
        }
        self.assertTrue(required.issubset(categories))
        inputs = {item["input"] for item in scenarios}
        self.assertIn("私の名前はのりこです。", inputs)
        self.assertIn("僕はチーズケーキが好きです。", inputs)
        self.assertIn("昨日話した映画。", inputs)

    def test_generalization_dataset_contains_required_categories_and_no_core_duplicates(self):
        generalization = load_extractor_scenarios(Path("eval_extractors/extractor_generalization_ja.jsonl"))
        core_inputs = {item["input"] for item in load_extractor_scenarios(Path("eval_extractors/extractor_core_ja.jsonl"))}
        required = {
            "identity_variation", "preference_variation", "time_expression", "future_plan",
            "conversation_bridge", "boundary", "emotion", "third_person", "unknown_name",
            "compound_word", "mixed_script", "colloquial", "ellipsis", "negation",
            "correction", "long_chunk", "short_utterance", "participant_reference",
        }
        self.assertGreaterEqual(len(generalization), 30)
        self.assertTrue(required.issubset({item["category"] for item in generalization}))
        self.assertFalse({item["input"] for item in generalization} & core_inputs)
        self.assertTrue(any(item.get("novel_terms") for item in generalization))
        self.assertTrue(any(item["category"] == "long_chunk" for item in generalization))

    def test_representative_scenario_scores_expected_words(self):
        item = {
            "scenario": "preference_cheesecake",
            "category": "Preference",
            "role": "user",
            "input": "僕はチーズケーキが好きです。",
            "expected_words": ["チーズケーキ", "好き"],
            "forbidden_words": ["です", "は"],
            "bridge_words": ["好き"],
            "compound_words": ["チーズケーキ"],
        }
        row = evaluate_extractor_scenario(item, FallbackTraceExtractor(), "fallback")
        self.assertEqual(row["expected_hit"], 2)
        self.assertEqual(row["bridge_hit"], 1)
        self.assertEqual(row["compound_hit"], 1)
        self.assertEqual(row["unexpected_hit"], 0)
        self.assertIn("normalized_words", row)
        self.assertIn("extracted_words", row)

    def test_generalization_diagnostics_are_calculated(self):
        item = {
            "scenario": "diagnostic_case",
            "category": "compound_word",
            "role": "user",
            "input": "バスクチーズケーキ食べたい",
            "expected_words": ["バスクチーズケーキ"],
            "novel_terms": ["バスクチーズケーキ"],
            "compound_words": ["バスクチーズケーキ"],
            "forbidden_words": [],
        }
        row = evaluate_extractor_scenario(item, FallbackTraceExtractor(), "fallback")
        self.assertIn("novel_term_exact_hit_count", row)
        self.assertIn("novel_term_partial_hit_count", row)
        self.assertIn("novel_term_missing_count", row)
        self.assertIn("long_token_count", row)
        self.assertIn("whole_sentence_like_token_count", row)


    def test_cli_generates_csv_markdown_and_jsonl_for_fallback_and_llm(self):
        scenario = Path("eval_extractors/extractor_core_ja.jsonl")
        for extractor in ("fallback", "llm", "local-rule"):
            with self.subTest(extractor=extractor), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp)
                args = argparse.Namespace(
                    extractor=extractor,
                    scenario=str(scenario),
                    base_url="",
                    api_key="",
                    model="local-model",
                    extractor_model="",
                    timeout=0.01,
                    debug_extractor=False,
                    metrics_csv=str(out / "metrics.csv"),
                    details_jsonl=str(out / "details.jsonl"),
                    report_md=str(out / "report.md"),
                )
                self.assertEqual(cmd_eval_extractor(args), 0)
                self.assertTrue((out / "metrics.csv").exists())
                self.assertTrue((out / "details.jsonl").exists())
                self.assertTrue((out / "report.md").exists())
                with (out / "metrics.csv").open(encoding="utf-8", newline="") as f:
                    self.assertGreater(len(list(csv.DictReader(f))), 0)
                first = json.loads((out / "details.jsonl").read_text(encoding="utf-8").splitlines()[0])
                self.assertIn("extracted_words", first)
                self.assertIn("normalized_words", first)
                report = (out / "report.md").read_text(encoding="utf-8")
                self.assertIn("Extractor Evaluation Report", report)
                self.assertIn("Category Summary", report)


if __name__ == "__main__":
    unittest.main()
