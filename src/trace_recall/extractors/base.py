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
    # Surface form remains the stored/displayed word. canonical_word is
    # metadata for language-aware matching and is not yet a storage key.
    canonical_word: str | None = None


class WordPolicy(Protocol):
    """Language-specific rules applied after candidate extraction."""

    def canonicalize(self, word: str) -> str:
        """Return the comparison form for a surface word."""

    def should_keep(self, word: str) -> bool:
        """Return whether the surface word is useful as a trace candidate."""


class IdentityWordPolicy:
    """Language-neutral policy preserving the current surface-word behavior."""

    def canonicalize(self, word: str) -> str:
        return word

    def should_keep(self, word: str) -> bool:
        return True


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



def finalize_extracted_words(
    words: list[ExtractedWord],
    policy: WordPolicy | None = None,
) -> list[ExtractedWord]:
    """Apply one language policy and deduplicate candidates by canonical form.

    The selected item's surface form is preserved in word so existing Memory
    storage and Recall behavior do not change. canonical_word is carried as
    metadata for a later, separately evaluated storage/Recall migration.
    Policy failures are intentionally propagated to the caller.
    """
    if policy is None:
        policy = IdentityWordPolicy()
    by_canonical: dict[str, ExtractedWord] = {}
    for item in words:
        surface = normalize_word(item.word)
        if not surface or not policy.should_keep(surface):
            continue
        canonical = normalize_word(policy.canonicalize(surface))
        if not canonical:
            continue
        candidate = ExtractedWord(
            word=surface,
            weight=clamp(float(item.weight), 0.1, 2.0),
            canonical_word=canonical if canonical != surface else None,
        )
        existing = by_canonical.get(canonical)
        if existing is None or candidate.weight > existing.weight:
            by_canonical[canonical] = candidate
    return sorted(
        by_canonical.values(),
        key=lambda item: item.weight,
        reverse=True,
    )


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
