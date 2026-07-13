"""Common extractor contracts for Trace Recall."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol


@dataclass
class ExtractedWord:
    word: str
    weight: float


@dataclass
class ExtractionResult:
    words: list[ExtractedWord]
    extractor_name: str


class TraceExtractor(Protocol):
    name: str

    def extract(self, text: str) -> list[ExtractedWord]:
        """Extract trace trigger words from text."""


def normalize_text(text: str) -> str:
    return text.strip().replace("　", " ")


def normalize_word(word: str) -> str:
    word = normalize_text(word)
    return word.strip(" \t\r\n。、,.!?！？「」『』（）()[]【】")


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def dedupe_extracted_words(words: list[ExtractedWord]) -> list[ExtractedWord]:
    d: dict[str, float] = {}
    for item in words:
        word = normalize_word(item.word)
        if not word:
            continue
        d[word] = max(d.get(word, 0.0), clamp(item.weight, 0.1, 2.0))
    return [ExtractedWord(w, weight) for w, weight in sorted(d.items(), key=lambda kv: kv[1], reverse=True)]


def parse_json_object(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM output.")
    return json.loads(match.group(0))
