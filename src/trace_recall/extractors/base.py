"""Common extractor contracts for Trace Recall."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


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


# failure_type values recorded by finalize_extracted_words().
POLICY_REJECTED = "rejected_by_policy"      # should_keep() returned False -> dropped
SHOULD_KEEP_ERROR = "should_keep_error"     # should_keep() raised -> kept as surface
CANONICALIZE_ERROR = "canonicalize_error"   # canonicalize() raised -> surface used as canonical
CANONICALIZE_EMPTY = "canonicalize_empty"   # canonicalize() returned empty -> surface used as canonical

ACTION_DROPPED = "dropped"
ACTION_KEPT_SURFACE = "kept_surface"


@dataclass
class WordPolicyEvent:
    """One visible record of a policy rejection or failure for a candidate.

    Rejection and failure share the failure_type field but use distinct
    values, and action states what happened to the candidate. Only
    should_keep() returning False drops a candidate; every failure keeps the
    surface form so a broken policy cannot silently remove traces.
    """

    surface: str
    failure_type: str
    action: str
    detail: str = ""


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
    events: list[WordPolicyEvent] | None = None,
) -> list[ExtractedWord]:
    """Apply one language policy and deduplicate candidates by canonical form.

    The selected item's surface form is preserved in word so existing Memory
    storage and Recall behavior do not change. canonical_word is carried as
    metadata for a later, separately evaluated storage/Recall migration.

    Policy rejections and failures are never silent. If ``events`` is given,
    one WordPolicyEvent is appended per rejected or failed candidate:

    - should_keep() returns False: candidate dropped (rejected_by_policy).
    - should_keep() raises: candidate kept (should_keep_error).
    - canonicalize() raises or returns an empty/non-string value: the surface
      form is used as the canonical form (canonicalize_error /
      canonicalize_empty).

    Only an explicit should_keep() == False drops a candidate.

    When ``events`` is not given, failures (not rejections) are still emitted
    as logging warnings so a broken policy is never invisible.
    """
    if policy is None:
        policy = IdentityWordPolicy()
    by_canonical: dict[str, ExtractedWord] = {}
    for item in words:
        surface = normalize_word(item.word)
        if not surface:
            continue
        try:
            keep = bool(policy.should_keep(surface))
        except Exception as exc:  # policy bug must not drop the trace
            keep = True
            _record_policy_event(events, surface, SHOULD_KEEP_ERROR, ACTION_KEPT_SURFACE, exc)
        if not keep:
            _record_policy_event(events, surface, POLICY_REJECTED, ACTION_DROPPED)
            continue
        try:
            canonical = normalize_word(policy.canonicalize(surface))
        except Exception as exc:  # includes non-string return values
            canonical = surface
            _record_policy_event(events, surface, CANONICALIZE_ERROR, ACTION_KEPT_SURFACE, exc)
        else:
            if not canonical:
                canonical = surface
                _record_policy_event(events, surface, CANONICALIZE_EMPTY, ACTION_KEPT_SURFACE)
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


def _record_policy_event(
    events: list[WordPolicyEvent] | None,
    surface: str,
    failure_type: str,
    action: str,
    exc: BaseException | None = None,
) -> None:
    detail = f"{type(exc).__name__}: {exc}" if exc is not None else ""
    if events is None:
        if failure_type != POLICY_REJECTED:
            logger.warning(
                "word policy %s for %r (%s)%s",
                failure_type, surface, action, f": {detail}" if detail else "",
            )
        return
    events.append(WordPolicyEvent(surface=surface, failure_type=failure_type, action=action, detail=detail))


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
