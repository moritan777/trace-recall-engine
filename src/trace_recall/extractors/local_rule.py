"""Deterministic local-rule Trace word extractor v0."""

from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass

from .base import ExtractedWord, normalize_word


# LocalRuleTraceExtractor is intentionally incomplete.
#
# Its goal is not full Japanese linguistic analysis.
# It preserves enough deterministic trace cues for downstream
# activation and gate selection to reconstruct useful recall.
#
# Slight over-extraction is acceptable.
# Broken names, lost compounds, missing bridge words,
# and empty extraction are treated as higher-cost failures.
#
# LocalRuleTraceExtractorは完全な日本語解析器ではない。
#
# 目的は、後段のActivationとGateが有用なRecallを成立させるための
# 決定論的なTrace手掛かりを十分に残すことである。
#
# 少し多めの抽出は許容する。
# 名前破損、複合語欠落、Bridge Word欠落、空抽出を
# より重大な失敗として扱う。


@dataclass(frozen=True)
class _Candidate:
    word: str
    weight: float
    pos: int
    source: str


class LocalRuleTraceExtractor:
    """Small deterministic extractor for local Trace candidate extraction."""

    name = "local-rule"
    requires_llm = False

    # Intentionally small bridge list: these are trace connection points, not a
    # semantic ontology or person dictionary.
    BRIDGE_WORDS = {
        "名前", "好き", "嫌い", "誕生日", "記念日", "約束", "予定", "仕事", "家族", "話", "映画",
        "紅茶", "コーヒー",
    }
    TIME_WORDS = {
        "今日", "昨日", "明日", "今度", "最近", "来週", "先週", "来月", "金曜日", "月曜日", "火曜日",
        "水曜日", "木曜日", "土曜日", "日曜日",
    }
    ACTION_PATTERNS = [
        r"見に行(?:く|こう|った|きたい)",
        r"迎えに行(?:く|こう|った|きたい)",
        r"話した", r"飲みたい", r"疲れた", r"眠れない", r"寂しかった", r"やめて", r"思う",
        r"大丈夫",
    ]
    STOP_WORDS = {
        "は", "が", "を", "に", "へ", "で", "と", "も", "の", "や", "です", "ます", "だ", "ね", "よ",
        "だった", "でした", "じゃなくて", "なくて", "一緒", "そう", "す",
    }

    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        self.last_diagnostics: dict[str, object] = {}

    def extract(self, text: str) -> list[ExtractedWord]:
        started = time.perf_counter()
        normalized = self._normalize_text(text)
        candidates: list[_Candidate] = []
        candidates.extend(self._protected_candidates(normalized))
        candidates.extend(self._chunk_candidates(normalized))
        words, removed = self._dedupe(candidates)
        self.last_diagnostics = {
            "extractor_name": self.name,
            "elapsed_ms": (time.perf_counter() - started) * 1000.0,
            "raw_candidates": [c.word for c in candidates],
            "final_words": [w.word for w in words],
            "removed_stop_words": removed,
            "compound_candidates": [c.word for c in candidates if c.source == "compound"],
            "bridge_candidates": [c.word for c in candidates if c.source == "bridge"],
        }
        return words

    def _normalize_text(self, text: str) -> str:
        text = unicodedata.normalize("NFKC", text or "")
        text = re.sub(r"[\t\r\n]+", " ", text)
        return re.sub(r" {2,}", " ", text).strip()

    def _protected_candidates(self, text: str) -> list[_Candidate]:
        out: list[_Candidate] = []
        # Future extension point: known Trace Memory words could be longest-match
        # candidates here without making the extractor depend on the DB in v0.
        for word in sorted(self.TIME_WORDS | self.BRIDGE_WORDS, key=len, reverse=True):
            for m in re.finditer(re.escape(word), text):
                out.append(_Candidate(word, 0.9, m.start(), "bridge" if word in self.BRIDGE_WORDS else "time"))
        for pat in self.ACTION_PATTERNS:
            for m in re.finditer(pat, text):
                word = m.group(0)
                if word.endswith("こう"):
                    word = word[:-2] + "く"
                out.append(_Candidate(word, 0.9, m.start(), "action"))
        for m in re.finditer(r"[A-Za-z0-9]+[ぁ-んァ-ン一-龥ー]+|[ァ-ンー]{3,}|[一-龥]{1,3}カノ", text):
            out.append(_Candidate(m.group(0), 1.0, m.start(), "compound"))
        return out

    def _chunk_candidates(self, text: str) -> list[_Candidate]:
        out: list[_Candidate] = []
        spans = re.finditer(r"[A-Za-z0-9ぁ-んァ-ン一-龥ー]+", text)
        for span in spans:
            chunk = span.group(0)
            parts = self._split_chunk(chunk)
            offset = span.start()
            cursor = 0
            for part in parts:
                local = chunk.find(part, cursor)
                cursor = local + len(part) if local >= 0 else cursor
                pos = offset + (local if local >= 0 else 0)
                cleaned = self._clean_surface(part)
                if cleaned:
                    for sub in cleaned.split("|"):
                        sub = self._clean_surface(sub)
                        if sub:
                            out.append(_Candidate(sub, 0.8, pos, "chunk"))
        return out

    def _split_chunk(self, chunk: str) -> list[str]:
        chunk = re.sub(r"(じゃなくて|なくて)", "|", chunk)
        protected = {m.span() for m in re.finditer(r"[ァ-ンー]{3,}|[A-Za-z0-9]+[ぁ-んァ-ン一-龥ー]+|見に行(?:く|こう)|迎えに行(?:く|こう)|話した|飲みたい|疲れた|眠れない|寂しかった|やめて|思う|大丈夫", chunk)}
        boundaries = []
        for i, ch in enumerate(chunk):
            if any(start <= i < end for start, end in protected):
                continue
            if ch in "はがをへも":
                boundaries.append(i)
            elif ch == "で" and chunk[i:i + 2] != "です":
                boundaries.append(i)
            elif ch == "や":
                boundaries.append(i)
            elif ch == "の" and i > 0 and chunk[i - 1] not in "はがをにへでもやの":
                boundaries.append(i)
            elif ch == "に" and not (i > 0 and chunk[i - 1] in "見迎"):
                boundaries.append(i)
        parts: list[str] = []
        start = 0
        for b in boundaries:
            if start < b:
                parts.append(chunk[start:b])
            start = b + 1
        if start < len(chunk):
            parts.append(chunk[start:])
        return parts

    def _clean_surface(self, word: str) -> str:
        word = normalize_word(word)
        if not word:
            return ""
        word = re.sub(r"(です|でした|だった|だよね|だね|だよ|ます)$", "", word)
        if word.endswith("だった") and len(word) > 3:
            word = word[:-3]
        return normalize_word(word)

    def _dedupe(self, candidates: list[_Candidate]) -> tuple[list[ExtractedWord], list[str]]:
        best: dict[str, tuple[float, int]] = {}
        removed: list[str] = []
        for c in candidates:
            word = self._clean_surface(c.word)
            if not word:
                continue
            if word in self.STOP_WORDS:
                removed.append(word)
                continue
            current = best.get(word)
            if current is None or c.weight > current[0]:
                best[word] = (c.weight, c.pos)
        ordered = sorted(best.items(), key=lambda kv: (kv[1][1], -kv[1][0], kv[0]))
        return [ExtractedWord(word, weight) for word, (weight, _pos) in ordered], removed
