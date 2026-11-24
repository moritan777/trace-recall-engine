"""Fallback Trace word extractor.

This module preserves the pre-refactor fallback extraction behavior.
"""

from __future__ import annotations

import re
import unicodedata

from .base import ExtractedWord, dedupe_extracted_words, normalize_text, normalize_word

# Latin letters including accented forms (Latin-1 Supplement and Latin
# Extended-A/B, e.g. á é ő ű), excluding the × and ÷ signs. Without these an
# accented letter acted as a word separator: "házakban" -> "h" + "zakban".
LATIN_WORD_CHARS = "A-Za-z0-9\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u024F"


class FallbackTraceExtractor:
    name = "fallback"

    def extract(self, text: str) -> list[ExtractedWord]:
        return fallback_extract_words(text)


def fallback_extract_words(text: str) -> list[ExtractedWord]:
    # NFC so a decomposed accent (a + U+0301) is one letter, not a separator.
    text = normalize_text(unicodedata.normalize("NFC", text))
    known_terms = [
        "チーズケーキ", "コーヒー", "紅茶", "好き",
        "カフェ", "帰り", "食べる", "映画", "ポップコーン",
        "カッターナイフ", "カッター", "怪我", "苦手", "昔",
        "誕生日", "記念日", "猫", "ペット", "ギター",
    ]

    found: list[ExtractedWord] = []
    for term in known_terms:
        if term in text:
            found.append(ExtractedWord(term, 1.2 if len(term) >= 4 else 1.0))

    if "ケーキ" in text and "チーズケーキ" not in [w.word for w in found]:
        found.append(ExtractedWord("ケーキ", 1.0))
    if "カッター" in text and "カッターナイフ" not in [w.word for w in found]:
        found.append(ExtractedWord("カッターナイフ", 0.9))

    chunks = re.findall(rf"[{LATIN_WORD_CHARS}]+|[ぁ-んァ-ン一-龥ー]{{2,}}", text)
    stop = {"です", "ます", "す", "だった", "って", "これ", "それ", "今日", "明日", "昨日", "する", "した", "ある", "いる", "もの", "なもの"}
    for ch in chunks:
        ch = normalize_word(ch)
        if not ch or ch in stop:
            continue
        should_keep_chunk = not (len(ch) >= 8 and re.search(r"[はがをにへでとてもやの]", ch))
        if should_keep_chunk and not any(ch in term and ch != term for term in known_terms):
            found.append(ExtractedWord(ch, 0.8))

        for part in split_japanese_particles(ch):
            part = normalize_word(part)
            if not part or part in stop or part == ch:
                continue
            if any(part in term and part != term for term in known_terms):
                continue
            found.append(ExtractedWord(part, 0.8))

    return dedupe_extracted_words(found)


def split_japanese_particles(text: str) -> list[str]:
    """Split lightweight Japanese fallback chunks without damaging word-initial 「の」."""
    split_particles = set("はがをにへでともや")
    boundary_particles = split_particles | {"の"}
    parts: list[str] = []
    start = 0
    for index, char in enumerate(text):
        should_split = char in split_particles
        if char == "の":
            previous = text[index - 1] if index > 0 else ""
            should_split = index > start and previous not in boundary_particles
        if should_split:
            if start < index:
                parts.append(text[start:index])
            start = index + 1
    if start < len(text):
        parts.append(text[start:])
    return parts
