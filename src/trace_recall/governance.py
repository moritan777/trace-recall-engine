"""Small, semantic-free contracts for recall governance and evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Protocol


class RecallExpectation(str, Enum):
    SHOULD_RECALL = "SHOULD_RECALL"
    MAY_RECALL = "MAY_RECALL"
    SHOULD_NOT_RECALL = "SHOULD_NOT_RECALL"
    MUST_NOT_SPEAK = "MUST_NOT_SPEAK"


class ConflictState(str, Enum):
    CURRENT = "CURRENT"
    HISTORICAL = "HISTORICAL"
    SUPERSEDED = "SUPERSEDED"
    CONFLICTED = "CONFLICTED"
    UNCERTAIN = "UNCERTAIN"


class RecallOutcome(str, Enum):
    NO_CANDIDATES = "NO_CANDIDATES"
    CANDIDATES_SUPPRESSED = "CANDIDATES_SUPPRESSED"
    CANDIDATES_SELECTED = "CANDIDATES_SELECTED"


class AdmissionAction(str, Enum):
    ALLOW = "ALLOW"
    SUPPRESS = "SUPPRESS"


@dataclass(frozen=True)
class AdmissionDecision:
    action: AdmissionAction
    reason: str = ""

    def __post_init__(self) -> None:
        if self.action is AdmissionAction.SUPPRESS and not self.reason.strip():
            raise ValueError("a suppression decision requires a reason")


class AdmissionHook(Protocol):
    """External policy boundary; candidate and context contain no domain semantics."""

    def __call__(self, candidate: Any, context: Mapping[str, Any]) -> AdmissionDecision: ...


def parse_expectation(value: str | RecallExpectation) -> RecallExpectation:
    if isinstance(value, RecallExpectation):
        return value
    return RecallExpectation(str(value).strip().upper())


def classify_outcome(candidate_count: int, selected_count: int) -> RecallOutcome:
    if candidate_count <= 0:
        return RecallOutcome.NO_CANDIDATES
    if selected_count <= 0:
        return RecallOutcome.CANDIDATES_SUPPRESSED
    return RecallOutcome.CANDIDATES_SELECTED


def evaluate_expectations(labels: Mapping[str, str | RecallExpectation], recalled: set[str], spoken: set[str] | None = None) -> dict[str, Any]:
    """Evaluate governance labels without interpreting or resolving trace meaning."""
    spoken = recalled if spoken is None else spoken
    parsed = {word: parse_expectation(label) for word, label in labels.items()}
    violations: list[dict[str, str]] = []
    for word, label in parsed.items():
        if label is RecallExpectation.SHOULD_RECALL and word not in recalled:
            violations.append({"word": word, "label": label.value, "reason": "not_recalled"})
        elif label is RecallExpectation.SHOULD_NOT_RECALL and word in recalled:
            violations.append({"word": word, "label": label.value, "reason": "recalled"})
        elif label is RecallExpectation.MUST_NOT_SPEAK and word in spoken:
            violations.append({"word": word, "label": label.value, "reason": "spoken"})
    return {"passed": not violations, "violations": violations, "labels": {k: v.value for k, v in parsed.items()}}
