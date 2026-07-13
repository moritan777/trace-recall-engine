"""Japanese Trace Tokenizer for deterministic Trace candidate generation.

This is not a morphological analyzer.  It only proposes recall-oriented
surface chunks by sentence, clause, and phrase boundaries while preserving
protected spans supplied by the extractor.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TokenCandidate:
    text: str
    start: int
    end: int
    source: str = "tokenizer"


class ProtectedSpanLike(Protocol):
    start: int
    end: int


class JapaneseTraceTokenizer:
    """Rule-and-character-type tokenizer for Japanese Trace candidates.

    ``tokenize`` continues to return only primary chunks.  Alternate spans are
    generated as diagnostics for oracle evaluation and are intentionally not
    consumed by the local-rule selector.
    """

    CONNECTIVE_BOUNDARIES = ("だけど", "じゃ", "それで", "すると", "だから", "なので", "でも", "けど", "のに")
    PARTICLE_BOUNDARIES = ("から", "まで", "など", "は", "が", "を", "に", "へ", "で", "と", "も", "の")
    SENTENCE_BOUNDARY_RE = re.compile(r"[。！？…\n]+")
    SURFACE_RE = re.compile(r"[A-Za-z0-9ぁ-んァ-ン一-龥ー._+\-/]+(?:\s+[A-Za-z0-9][A-Za-z0-9._+\-/]*)*")
    SHORT_KEEP_LENGTH = 4
    MIN_SPLIT_LENGTH = 5
    MAX_ALTERNATE_LENGTH = 12
    MAX_ALTERNATES_PER_START = 3

    def __init__(self) -> None:
        self.last_diagnostics: dict[str, object] = {}
        self.last_primary_chunks: list[TokenCandidate] = []
        self.last_alternate_spans: list[TokenCandidate] = []

    def tokenize(self, text: str, protected_spans: list[ProtectedSpanLike] | None = None) -> list[TokenCandidate]:
        protected_ranges = [(s.start, s.end) for s in (protected_spans or [])]
        tokens: list[TokenCandidate] = []
        split_count = 0
        for start, end in self._sentence_segments(text):
            for surf in self.SURFACE_RE.finditer(text, start, end):
                for seg_start, seg_end in self._residual_segments(surf.start(), surf.end(), protected_ranges):
                    phrase = text[seg_start:seg_end]
                    pieces = self._split_phrase(phrase, seg_start, protected_ranges)
                    split_count += max(0, len(pieces) - 1)
                    tokens.extend(pieces)
        alternates = self._alternate_spans(text, tokens, protected_ranges)
        self.last_primary_chunks = tokens
        self.last_alternate_spans = alternates
        lengths = [len(t.text) for t in tokens]
        alt_lengths = [len(t.text) for t in alternates]
        self.last_diagnostics = {
            "tokenizer_candidate_count": len(tokens),
            "average_candidate_length": (sum(lengths) / len(lengths)) if lengths else 0.0,
            "tokenizer_split_count": split_count,
            "average_chunk_length": (sum(lengths) / len(lengths)) if lengths else 0.0,
            "tokenizer_primary_chunks": [t.text for t in tokens],
            "tokenizer_alternate_spans": [t.text for t in alternates],
            "tokenizer_alternate_count": len(alternates),
            "average_alternate_length": (sum(alt_lengths) / len(alt_lengths)) if alt_lengths else 0.0,
        }
        return tokens


    def _alternate_spans(self, text: str, primary: list[TokenCandidate], protected_ranges: list[tuple[int, int]]) -> list[TokenCandidate]:
        spans: dict[tuple[int, int, str], TokenCandidate] = {}
        def add(raw: str, start: int) -> None:
            cleaned = raw.strip(" 　、,.;:()（）[]【】『』\"'").lstrip("はがをにへでもや").rstrip("はがをにへでもやの")
            if not cleaned or len(cleaned) > self.MAX_ALTERNATE_LENGTH:
                return
            local = raw.find(cleaned)
            real_start = start + (local if local >= 0 else 0)
            key = (real_start, real_start + len(cleaned), cleaned)
            # Bound the generator: at most three alternates sharing the same start.
            if sum(1 for s, _e, _w in spans if s == real_start) >= self.MAX_ALTERNATES_PER_START:
                return
            spans[key] = TokenCandidate(cleaned, key[0], key[1], "alternate")

        for token in primary:
            self._alternate_from_chunk(token.text, token.start, add)

        # Also inspect residual surface spans so alternates can explain words lost
        # inside a long primary chunk without enumerating all start/end pairs.
        for start, end in self._sentence_segments(text):
            for surf in self.SURFACE_RE.finditer(text, start, end):
                for seg_start, seg_end in self._residual_segments(surf.start(), surf.end(), protected_ranges):
                    self._alternate_from_chunk(text[seg_start:seg_end], seg_start, add)
        return sorted(spans.values(), key=lambda t: (t.start, t.end, t.text))

    def _alternate_from_chunk(self, chunk: str, offset: int, add) -> None:
        if not chunk:
            return
        trimmed = re.sub(r"(っていう|って|やで|かな|だよ|だね|です|ます|なんだ)$", "", chunk)
        if trimmed != chunk:
            add(trimmed, offset)
        if len(chunk) > 2 and chunk[-1] in "なねよわで" and not chunk[-2:].isascii():
            add(chunk[:-1], offset)

        for m in re.finditer(r"[A-Za-z0-9]+|[ァ-ンー]+|[一-龥]+|[ぁ-ん]+", chunk):
            part = m.group(0)
            if 1 < len(part) <= self.MAX_ALTERNATE_LENGTH:
                add(part, offset + m.start())

        # Limited boundary-derived windows; no all-start x all-end enumeration.
        starts = {0}
        for marker in ("うち", "前", "後", "末"):
            idx = chunk.find(marker)
            if idx >= 0:
                starts.add(idx)
                starts.add(idx + len(marker))
        for i in range(1, len(chunk)):
            prev, cur = chunk[i - 1], chunk[i]
            if prev.isascii() != cur.isascii() or cur in "見観迎":
                starts.add(i)
        for st in sorted(x for x in starts if 0 <= x < len(chunk)):
            emitted = 0
            for pat in (r"(?:近いうち|今週末|この前|仕事帰り)", r"[A-Za-z0-9]+[ぁ-んァ-ン一-龥ー]+", r"[ァ-ンー一-龥]{2,}", r"[見観迎]にい?こ(?:う)?"):
                m = re.match(pat, chunk[st:])
                if m:
                    add(m.group(0), offset + st)
                    emitted += 1
                    if emitted >= self.MAX_ALTERNATES_PER_START:
                        break

    def _sentence_segments(self, text: str) -> list[tuple[int, int]]:
        segments: list[tuple[int, int]] = []
        start = 0
        for m in self.SENTENCE_BOUNDARY_RE.finditer(text):
            if start < m.start():
                segments.append((start, m.start()))
            start = m.end()
        if start < len(text):
            segments.append((start, len(text)))
        return segments

    def _split_phrase(self, phrase: str, offset: int, protected_ranges: list[tuple[int, int]]) -> list[TokenCandidate]:
        if len(phrase) <= self.SHORT_KEEP_LENGTH:
            return self._emit_one(phrase, offset)
        boundaries = self._boundary_positions(phrase, offset, protected_ranges)
        pieces: list[TokenCandidate] = []
        start = 0
        for b_start, b_end in boundaries:
            if start < b_start:
                pieces.extend(self._emit_one(phrase[start:b_start], offset + start))
            start = b_end
        if start < len(phrase):
            pieces.extend(self._emit_one(phrase[start:], offset + start))
        return pieces or self._emit_one(phrase, offset)

    def _boundary_positions(self, phrase: str, offset: int, protected_ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        i = 0
        while i < len(phrase):
            if self._in_protected(offset + i, protected_ranges):
                i += 1
                continue
            matched = None
            for word in self.CONNECTIVE_BOUNDARIES + self.PARTICLE_BOUNDARIES:
                if phrase.startswith(word, i) and self._is_safe_boundary(phrase, i, i + len(word), word):
                    matched = word
                    break
            if matched:
                out.append((i, i + len(matched)))
                i += len(matched)
            elif i >= 2 and phrase[i] in "見観迎" and phrase[i + 1:i + 2] == "に":
                out.append((i, i))
                i += 1
            else:
                i += 1
        return out

    def _is_safe_boundary(self, phrase: str, start: int, end: int, word: str) -> bool:
        if len(phrase) < self.MIN_SPLIT_LENGTH:
            return False
        prev = phrase[start - 1] if start > 0 else ""
        nxt = phrase[end] if end < len(phrase) else ""
        if not prev:
            return False
        if not nxt:
            return word in {"の", "は", "が", "を", "に", "へ", "で", "と", "も"}
        if word == "の" and (prev in "はがをにへでもやの" or re.fullmatch(r"[ぁ-ん]", prev)):
            return False
        if word == "に" and prev in "見観迎" and nxt in "行い":
            return False
        if word == "で" and phrase.startswith("です", start):
            return False
        if word == "と" and nxt in "思話言":
            return False
        if word == "が" and prev.isascii() and nxt.isascii():
            return False
        return True

    def _emit_one(self, text: str, start: int) -> list[TokenCandidate]:
        cleaned = text.strip(" 　、,.;:()（）[]【】『』\"'").lstrip("はがをにへでもや").rstrip("はがをにへでもやの")
        if not cleaned:
            return []
        local = text.find(cleaned)
        real_start = start + (local if local >= 0 else 0)
        return [TokenCandidate(cleaned, real_start, real_start + len(cleaned))]

    def _in_protected(self, pos: int, ranges: list[tuple[int, int]]) -> bool:
        return any(start <= pos < end for start, end in ranges)

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
