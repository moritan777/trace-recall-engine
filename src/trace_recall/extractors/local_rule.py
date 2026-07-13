"""Deterministic local-rule Trace word extractor v0."""

from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Protocol

from .base import ExtractedWord, normalize_word
from .japanese_trace_tokenizer import JapaneseTraceTokenizer


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


@dataclass(frozen=True)
class _ProtectedSpan:
    start: int
    end: int
    word: str
    weight: float
    source: str


class TraceVocabularyProvider(Protocol):
    """Provides a memory mirror of words already stored in the Trace DB."""

    def get_trace_vocabulary(self) -> list[tuple[str, float]]:
        """Return normalized (word, score) candidates without creating a new dictionary DB."""


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

    def __init__(self, debug: bool = False, trace_vocabulary: TraceVocabularyProvider | None = None) -> None:
        self.debug = debug
        self.trace_vocabulary = trace_vocabulary
        self.tokenizer = JapaneseTraceTokenizer()
        self.last_diagnostics: dict[str, object] = {}

    def set_trace_vocabulary_provider(self, provider: TraceVocabularyProvider | None) -> None:
        self.trace_vocabulary = provider

    def extract(self, text: str) -> list[ExtractedWord]:
        started = time.perf_counter()
        normalized = self._normalize_text(text)
        protected_spans = self._protected_spans(normalized)
        candidates: list[_Candidate] = [_Candidate(s.word, s.weight, s.start, s.source) for s in protected_spans]
        tokenizer_tokens = self.tokenizer.tokenize(normalized, protected_spans)
        candidates.extend(self._chunk_candidates(normalized, protected_spans, tokenizer_tokens))
        words, removed = self._dedupe(candidates)
        self.last_diagnostics = {
            "extractor_name": self.name,
            "elapsed_ms": (time.perf_counter() - started) * 1000.0,
            "raw_candidates": [c.word for c in candidates],
            "final_words": [w.word for w in words],
            "removed_stop_words": removed,
            "compound_candidates": [c.word for c in candidates if c.source == "compound"],
            "bridge_candidates": [c.word for c in candidates if c.source == "bridge"],
            "protected_match_count": len(protected_spans),
            "protected_match_length": sum(s.end - s.start for s in protected_spans),
            "db_dictionary_hit_rate": self._db_dictionary_hit_rate(protected_spans),
            "longest_match_success": self._longest_match_success(normalized, protected_spans),
            "dictionary_coverage": self._dictionary_coverage(normalized),
            "protected_spans": [(s.word, s.start, s.end, s.source) for s in protected_spans],
            "oracle_primary_chunks": [s.word for s in protected_spans] + [t.text for t in tokenizer_tokens],
            **self.tokenizer.last_diagnostics,
            "chunks_accepted": len(words),
            "chunks_rejected": len(removed),
        }
        return words

    def _normalize_text(self, text: str) -> str:
        text = unicodedata.normalize("NFKC", text or "")
        text = re.sub(r"[\t\r\n]+", " ", text)
        return re.sub(r" {2,}", " ", text).strip()

    def _protected_spans(self, text: str) -> list[_ProtectedSpan]:
        spans: list[_ProtectedSpan] = []
        spans.extend(self._trace_dictionary_spans(text))
        spans.extend(self._built_in_protected_spans(text))
        return self._select_longest_non_overlapping(spans)

    def _trace_dictionary_spans(self, text: str) -> list[_ProtectedSpan]:
        if self.trace_vocabulary is None:
            return []
        out: list[_ProtectedSpan] = []
        for word, score in self.trace_vocabulary.get_trace_vocabulary():
            word = self._clean_surface(word)
            if not self._is_dictionary_candidate(word):
                continue
            for m in re.finditer(re.escape(word), text):
                out.append(_ProtectedSpan(m.start(), m.end(), word, min(max(score, 0.1), 2.0), "trace_dictionary"))
        return out

    def _built_in_protected_spans(self, text: str) -> list[_ProtectedSpan]:
        out: list[_ProtectedSpan] = []
        for word in sorted(self.TIME_WORDS | self.BRIDGE_WORDS, key=len, reverse=True):
            for m in re.finditer(re.escape(word), text):
                out.append(_ProtectedSpan(m.start(), m.end(), word, 0.9, "bridge" if word in self.BRIDGE_WORDS else "time"))
        for pat in self.ACTION_PATTERNS:
            for m in re.finditer(pat, text):
                word = m.group(0)
                if word.endswith("こう"):
                    word = word[:-2] + "く"
                out.append(_ProtectedSpan(m.start(), m.end(), word, 0.9, "action"))
        patterns = [
            (r"https?://[^\s　]+", "url", 1.0),
            (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "email", 1.0),
            (r"\d{4}年\d{1,2}月\d{1,2}日|\d{4}[-/]\d{1,2}[-/]\d{1,2}", "date", 1.0),
            (r"[A-Za-z0-9]+[ぁ-んァ-ン一-龥ー]+", "mixed_script", 1.0),
            (r"[ァ-ンー]{3,}|[一-龥]{1,3}カノ", "compound", 1.0),
        ]
        for pat, source, weight in patterns:
            for m in re.finditer(pat, text):
                out.append(_ProtectedSpan(m.start(), m.end(), m.group(0), weight, source))
        return out

    def _select_longest_non_overlapping(self, spans: list[_ProtectedSpan]) -> list[_ProtectedSpan]:
        selected: list[_ProtectedSpan] = []
        occupied: set[int] = set()
        for span in sorted(spans, key=lambda s: (0 if s.source == "trace_dictionary" else 1, -(s.end - s.start), -s.weight, s.start, s.word)):
            positions = set(range(span.start, span.end))
            if occupied & positions:
                continue
            selected.append(span)
            occupied |= positions
        return sorted(selected, key=lambda s: s.start)

    def _is_dictionary_candidate(self, word: str) -> bool:
        return len(word) >= 2 and word not in self.STOP_WORDS and not re.fullmatch(r"[\W_]+", word)

    def _db_dictionary_hit_rate(self, spans: list[_ProtectedSpan]) -> float:
        db_hits = sum(1 for s in spans if s.source == "trace_dictionary")
        return (db_hits / len(spans)) if spans else 0.0

    def _longest_match_success(self, text: str, spans: list[_ProtectedSpan]) -> bool:
        if self.trace_vocabulary is None:
            return True
        selected = {(s.start, s.end, s.word) for s in spans}
        by_start: dict[int, int] = {}
        for word, _score in self.trace_vocabulary.get_trace_vocabulary():
            word = self._clean_surface(word)
            if not self._is_dictionary_candidate(word):
                continue
            for m in re.finditer(re.escape(word), text):
                by_start[m.start()] = max(by_start.get(m.start(), 0), m.end() - m.start())
        for start, length in by_start.items():
            if not any(s == start and e - s == length for s, e, _w in selected):
                return False
        return True

    def _dictionary_coverage(self, text: str) -> float:
        if self.trace_vocabulary is None or not text:
            return 0.0
        covered: set[int] = set()
        for word, _score in self.trace_vocabulary.get_trace_vocabulary():
            word = self._clean_surface(word)
            if not self._is_dictionary_candidate(word):
                continue
            for m in re.finditer(re.escape(word), text):
                covered.update(range(m.start(), m.end()))
        return len(covered) / len(text)

    def _chunk_candidates(self, text: str, protected_spans: list[_ProtectedSpan] | None = None, tokenizer_tokens: list[object] | None = None) -> list[_Candidate]:
        out: list[_Candidate] = []
        protected_spans = protected_spans or []
        for token in tokenizer_tokens or self.tokenizer.tokenize(text, protected_spans):
            cleaned = self._clean_surface(getattr(token, "text", ""))
            if cleaned:
                out.append(_Candidate(cleaned, 0.8, int(getattr(token, "start", 0)), "tokenizer"))
        return out


    def _residual_segments(self, start: int, end: int, protected_ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
        overlaps = sorted((max(start, a), min(end, b)) for a, b in protected_ranges if a < end and b > start)
        if not overlaps:
            return [(start, end)]
        residuals: list[tuple[int, int]] = []
        cursor = start
        for a, b in overlaps:
            if cursor < a:
                residuals.append((cursor, a))
            cursor = max(cursor, b)
        if cursor < end:
            residuals.append((cursor, end))
        return residuals

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
