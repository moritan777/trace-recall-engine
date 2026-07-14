import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from threaded_concept_memory_probe import main  # noqa: E402


class EvalParserInheritanceTests(unittest.TestCase):
    def make_conversation(self, tmp: Path) -> Path:
        tmp.mkdir(parents=True, exist_ok=True)
        conversation = tmp / "conversation.jsonl"
        conversation.write_text(
            json.dumps(
                {
                    "turn": 1,
                    "role": "user",
                    "text": "テスト入力です。",
                    "mode": "ask_no_response",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        return conversation

    def run_eval_and_capture_generator(self, tmp: Path, argv_prefix: list[str], argv_suffix: list[str]) -> dict[str, object]:
        captured: dict[str, object] = {}

        def capture_init(self, base_url: str = "", api_key: str = "", model: str = "local-model", timeout_sec: float = 12.0) -> None:
            captured.update(
                {
                    "base_url": base_url,
                    "api_key": api_key,
                    "model": model,
                    "timeout_sec": timeout_sec,
                }
            )

        conversation = self.make_conversation(tmp)
        argv = [
            *argv_prefix,
            "eval",
            "--conversation-file", str(conversation),
            "--db", str(tmp / "memory.db"),
            "--events-jsonl", str(tmp / "events.jsonl"),
            "--metrics-csv", str(tmp / "metrics.csv"),
            "--report-md", str(tmp / "report.md"),
            "--extractor", "fallback",
            *argv_suffix,
        ]
        with patch("threaded_concept_memory_probe.ResponseGenerator.__init__", capture_init):
            self.assertEqual(main(argv), 0)
        return captured

    def test_eval_global_and_subcommand_llm_options_reach_response_generator_equally(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            global_config = self.run_eval_and_capture_generator(
                tmp / "global",
                [
                    "--base-url", "http://example.test",
                    "--chat-base-url", "http://chat.example.test/v1",
                    "--api-key", "global-key",
                    "--model", "global-model",
                    "--response-model", "global-response-model",
                    "--timeout", "3.5",
                ],
                [],
            )
            subcommand_config = self.run_eval_and_capture_generator(
                tmp / "subcommand",
                [],
                [
                    "--base-url", "http://example.test",
                    "--chat-base-url", "http://chat.example.test/v1",
                    "--api-key", "global-key",
                    "--model", "global-model",
                    "--response-model", "global-response-model",
                    "--timeout", "3.5",
                ],
            )

        self.assertEqual(global_config, subcommand_config)
        self.assertEqual(
            global_config,
            {
                "base_url": "http://chat.example.test/v1",
                "api_key": "global-key",
                "model": "global-response-model",
                "timeout_sec": 3.5,
            },
        )

    def test_eval_subcommand_empty_defaults_do_not_overwrite_global_base_url(self):
        with tempfile.TemporaryDirectory() as td:
            captured = self.run_eval_and_capture_generator(
                Path(td),
                ["--base-url", "http://example.test", "--model", "global-model"],
                [],
            )

        self.assertEqual(captured["base_url"], "http://example.test/v1")
        self.assertEqual(captured["model"], "global-model")


if __name__ == "__main__":
    unittest.main()
