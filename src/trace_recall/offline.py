"""Offline-only selector experiments. Nothing here is used by production recall."""

from __future__ import annotations

from typing import Iterable


def lateral_inhibition(candidates: Iterable[tuple[str, float]], ratio: float = 0.35) -> list[str]:
    """Keep candidates within ``ratio`` of the strongest score for Oracle Replay."""
    values = [(word, float(score)) for word, score in candidates]
    if not values:
        return []
    strongest = max(score for _, score in values)
    return [word for word, score in values if score >= strongest * ratio]


def compare_lateral_inhibition(candidates: Iterable[tuple[str, float]], expected: set[str], unexpected: set[str], ratio: float = 0.35) -> dict[str, int | list[str]]:
    """Report replay trade-offs without changing any production selector."""
    baseline = [word for word, _ in candidates]
    selected = lateral_inhibition(candidates, ratio)
    return {
        "selected": selected,
        "expected_hit_gain_loss": len(set(selected) & expected) - len(set(baseline) & expected),
        "unexpected_hit_reduction": len(set(baseline) & unexpected) - len(set(selected) & unexpected),
        "selected_word_count": len(selected),
        "prompt_size_impact": len(selected) - len(baseline),
        "counterexample_count": sum(1 for word in baseline if word in expected and word not in selected),
    }
