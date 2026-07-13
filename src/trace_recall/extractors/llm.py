"""LLM-backed Trace word extractor.

This module preserves the pre-refactor LLM extraction prompt and post-processing.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Callable

from .base import ExtractedWord, clamp, dedupe_extracted_words, normalize_word, parse_json_object
from .fallback import fallback_extract_words

ChatClient = Callable[..., str]


class LLMTraceExtractor:
    name = "llm"

    def __init__(self, base_url: str = "", api_key: str = "", model: str = "local-model", timeout_sec: float = 12.0, debug: bool = False, chat_client: ChatClient | None = None, normalize_base_url: Callable[[str], str] | None = None) -> None:
        if normalize_base_url is None:
            normalize_base_url = lambda value: value.rstrip("/")
        self.base_url = normalize_base_url(base_url or os.getenv("LLM_BASE_URL", ""))
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.model = model or os.getenv("LLM_MODEL", "local-model")
        self.timeout_sec = timeout_sec
        self.debug = debug or os.getenv("LLM_EXTRACTOR_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
        self.chat_client = chat_client

    def extract(self, text: str) -> list[ExtractedWord]:
        if self.base_url:
            try:
                print(f"[llm] extracting words via {self.base_url} model={self.model}", file=sys.stderr)
                return self._extract_with_llm(text)
            except Exception as exc:
                print(f"[warn] LLM word extraction failed, fallback used: {exc}", file=sys.stderr)
        return fallback_extract_words(text)

    def _extract_with_llm(self, text: str) -> list[ExtractedWord]:
        system = (
            "You extract Japanese memory trigger words from an utterance.\n"
            "\n"
            "Do not classify words.\n"
            "Do not infer relationship labels.\n"
            "Do not rewrite the utterance as a summary.\n"
            "Return strict JSON only.\n"
            "\n"
            "Schema:\n"
            "{\"words\":[{\"word\":\"...\",\"weight\":1.0}]}\n"
            "\n"
            "Extract short words that may be useful for reconnecting the experience later.\n"
            "\n"
            "Include:\n"
            "- people\n"
            "- objects\n"
            "- actions\n"
            "- places\n"
            "- feelings\n"
            "- time expressions\n"
            "- notable nouns, verbs, and adjectives\n"
            "- short relational bridge words when they are necessary to reconnect concrete entities later\n"
            "\n"
            "A relational bridge word is an ordinary word such as:\n"
            "名前, 好き, 嫌い, 誕生日, 約束, 仕事, 家族, 予定\n"
            "\n"
            "Do not return only the most specific proper noun when a short bridge word is necessary to reconstruct the connection later.\n"
            "\n"
            "Keep words short.\n"
            "Use base/common forms when natural.\n"
            "Avoid full sentences and long phrases.\n"
            "\n"
            "Weight range: 0.4 to 1.4.\n"
            "Important concrete words may use 1.2 to 1.4.\n"
            "Bridge words should normally use about 0.8 to 1.1.\n"
            "\n"
            "Examples:\n"
            "\n"
            "Input:\n"
            "私の名前はのりこです。\n"
            "\n"
            "Output:\n"
            "{\"words\":[\n"
            "  {\"word\":\"名前\",\"weight\":1.0},\n"
            "  {\"word\":\"のりこ\",\"weight\":1.4}\n"
            "]}\n"
            "\n"
            "Input:\n"
            "僕の名前はみつきです。\n"
            "\n"
            "Output:\n"
            "{\"words\":[\n"
            "  {\"word\":\"名前\",\"weight\":1.0},\n"
            "  {\"word\":\"みつき\",\"weight\":1.4}\n"
            "]}\n"
            "\n"
            "Input:\n"
            "僕はチーズケーキが好きです。\n"
            "\n"
            "Output:\n"
            "{\"words\":[\n"
            "  {\"word\":\"チーズケーキ\",\"weight\":1.4},\n"
            "  {\"word\":\"好き\",\"weight\":1.0}\n"
            "]}\n"
            "\n"
            "Input:\n"
            "今度一緒に映画を見に行こうね。\n"
            "\n"
            "Output:\n"
            "{\"words\":[\n"
            "  {\"word\":\"今度\",\"weight\":0.9},\n"
            "  {\"word\":\"映画\",\"weight\":1.3},\n"
            "  {\"word\":\"見に行く\",\"weight\":1.0}\n"
            "]}\n"
            "\n"
            "Return JSON only."
        )
        user_message = f"Input:\n{text}\n\nReturn JSON only."
        if self.debug:
            print("[LLM Extractor Debug] system prompt BEGIN", file=sys.stderr)
            print(system, file=sys.stderr)
            print("[LLM Extractor Debug] system prompt END", file=sys.stderr)
            print("[LLM Extractor Debug] user message BEGIN", file=sys.stderr)
            print(user_message, file=sys.stderr)
            print("[LLM Extractor Debug] user message END", file=sys.stderr)

        content = self.chat_client(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            temperature=0.0,
            max_tokens=256,
            timeout_sec=self.timeout_sec,
        )
        if self.debug:
            print("[LLM Extractor Debug] raw response BEGIN", file=sys.stderr)
            print(content, file=sys.stderr)
            print("[LLM Extractor Debug] raw response END", file=sys.stderr)

        data = parse_json_object(content)
        words_raw = data.get("words", [])
        if self.debug:
            print("[LLM Extractor Debug] parsed words raw=" + json.dumps(words_raw, ensure_ascii=False), file=sys.stderr)
        words: list[ExtractedWord] = []
        removed_items: list[Any] = []
        for item in words_raw:
            if not isinstance(item, dict):
                removed_items.append(item)
                continue
            word = normalize_word(str(item.get("word", "")))
            if not word:
                removed_items.append(item)
                continue
            try:
                weight = float(item.get("weight", 1.0))
            except Exception:
                weight = 1.0
            words.append(ExtractedWord(word, clamp(weight, 0.1, 2.0)))
        deduped_words = dedupe_extracted_words(words)
        final_words = deduped_words or fallback_extract_words(text)
        if self.debug:
            print("[LLM Extractor Debug] python normalized words=" + json.dumps([w.__dict__ for w in words], ensure_ascii=False), file=sys.stderr)
            print("[LLM Extractor Debug] python removed items=" + json.dumps(removed_items, ensure_ascii=False), file=sys.stderr)
            print("[LLM Extractor Debug] final words=" + json.dumps([w.__dict__ for w in final_words], ensure_ascii=False), file=sys.stderr)
            print(f"[LLM Extractor Debug] contains 名前 after python filter={'名前' in {w.word for w in final_words}}", file=sys.stderr)
        return final_words

