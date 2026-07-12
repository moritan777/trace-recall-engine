import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from threaded_concept_memory_probe import main  # noqa: E402


class ResearchLoggerTests(unittest.TestCase):
    def make_conversation(self, tmp: Path) -> Path:
        conversation = tmp / "conversation.jsonl"
        conversation.write_text(
            '\n'.join([
                json.dumps({"turn": 1, "role": "user", "text": "私の名前はみつきです。", "mode": "learn"}, ensure_ascii=False),
                json.dumps({"turn": 2, "role": "user", "text": "私の名前は何？", "mode": "ask", "expected_words": ["みつき"], "unexpected_words": ["太郎"]}, ensure_ascii=False),
            ]) + '\n',
            encoding="utf-8",
        )
        return conversation

    def run_eval(self, tmp: Path, *extra: str) -> Path:
        conversation = self.make_conversation(tmp)
        research_log = tmp / "research_log.jsonl"
        rc = main([
            "eval",
            "--conversation-file", str(conversation),
            "--db", str(tmp / "memory.db"),
            "--events-jsonl", str(tmp / "events.jsonl"),
            "--metrics-csv", str(tmp / "metrics.csv"),
            "--report-md", str(tmp / "report.md"),
            "--research-log-jsonl", str(research_log),
            "--research-log-dir", str(tmp / "research_log"),
            *extra,
        ])
        self.assertEqual(rc, 0)
        return research_log

    def test_eval_research_log_records_prompt_response_and_utf8(self):
        with tempfile.TemporaryDirectory() as td:
            log_path = self.run_eval(Path(td))
            text = log_path.read_text(encoding="utf-8")
            record = json.loads(text)

            self.assertIn("私の名前は何？", text)
            self.assertEqual(record["input_text"], "私の名前は何？")
            self.assertTrue(record["prompt"]["text"])
            self.assertTrue(record["response"]["text"])
            self.assertFalse(record["response"]["skipped"])
            self.assertEqual(record["evaluation"]["expected_words"], ["みつき"])
            self.assertIn("selected_thread_groups", record["recall"])
            self.assertTrue((Path(td) / "research_log" / "turn_0002.md").exists())

    def test_eval_research_log_records_no_response(self):
        with tempfile.TemporaryDirectory() as td:
            log_path = self.run_eval(Path(td), "--no-response")
            record = json.loads(log_path.read_text(encoding="utf-8"))

            self.assertTrue(record["response"]["skipped"])
            self.assertEqual(record["response"]["text"], "")
            self.assertTrue(record["prompt"]["rough_tokens"] > 0)

    def test_sensitivity_save_research_log_writes_each_trial(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            conversation = self.make_conversation(tmp)
            out = tmp / "sensitivity"
            rc = main([
                "sensitivity",
                "--conversation-file", str(conversation),
                "--output-dir", str(out),
                "--dimension", "prompt_view",
                "--values", "threadgroup,edge",
                "--save-research-log",
                "--no-response",
            ])
            self.assertEqual(rc, 0)
            self.assertTrue((out / "trials" / "threadgroup" / "research_log.jsonl").exists())
            self.assertTrue((out / "trials" / "edge" / "research_log.jsonl").exists())
            record = json.loads((out / "trials" / "edge" / "research_log.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(record["comparison_value"], "edge")
            self.assertTrue(record["response"]["skipped"])


if __name__ == "__main__":
    unittest.main()
