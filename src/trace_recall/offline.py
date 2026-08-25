"""Offline-only selector experiments. Nothing here is used by production recall."""

from __future__ import annotations

from enum import Enum
from typing import Any, Iterable, Mapping


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


class CompositionStrategy(str, Enum):
    """Offline-only group ordering experiments."""

    BASELINE = "BASELINE"
    DIRECT_MATCH_CAP = "DIRECT_MATCH_CAP"
    GROUP_DIVERSITY = "GROUP_DIVERSITY"
    GENERIC_WORD_DOWNWEIGHT = "GENERIC_WORD_DOWNWEIGHT"


def _group_id(group: Mapping[str, Any]) -> str:
    return str(group.get("canonical_key", group.get("representative_thread_id", "")))


def _words(group: Mapping[str, Any], key: str = "words") -> set[str]:
    value = group.get(key, [])
    return {str(word) for word in value} if isinstance(value, list) else set()


def _source_threads(group: Mapping[str, Any]) -> set[str]:
    values = group.get("member_thread_ids", [])
    if isinstance(values, list) and values:
        return {str(value) for value in values}
    representative = group.get("representative_thread_id")
    return {str(representative)} if representative is not None else set()


def group_competition_analysis(
    groups: Iterable[Mapping[str, Any]], targets: Iterable[str], selected_group_ids: Iterable[str]
) -> dict[str, Any]:
    """Describe observed competition at the ThreadGroup boundary."""
    candidates = [dict(group) for group in groups]
    selected_ids = {str(value) for value in selected_group_ids}
    targets = {str(value) for value in targets}
    selected = [group for group in candidates if _group_id(group) in selected_ids]
    details = []
    for group in candidates:
        words = _words(group)
        direct = _words(group, "direct_words")
        people = _words(group, "person_name_words")
        generic = _words(group, "generic_words")
        overlaps = [
            {"group_id": _group_id(other), "word_count": len(words & _words(other))}
            for other in candidates if other is not group and words & _words(other)
        ]
        details.append({
            "group_id": _group_id(group), "selected": _group_id(group) in selected_ids,
            "contains_target": bool(words & targets),
            "group_score": float(group.get("group_score", group.get("score", 0.0)) or 0.0),
            "direct_match_contribution": len(direct), "person_name_contribution": len(people),
            "generic_word_contribution": len(generic),
            "distinct_source_thread_count": len(_source_threads(group)), "group_overlap": overlaps,
        })
    return {
        "selected_group_count": len(selected), "candidate_groups_considered": len(candidates),
        "groups": details,
    }


def _offline_score(group: Mapping[str, Any], strategy: CompositionStrategy) -> float:
    score = float(group.get("group_score", group.get("score", 0.0)) or 0.0)
    if strategy is CompositionStrategy.GENERIC_WORD_DOWNWEIGHT:
        # This is deliberately an offline composition adjustment, not a new
        # production word or connection weight.
        score -= .5 * sum(float(v) for v in (group.get("generic_word_scores", {}) or {}).values())
        if not group.get("generic_word_scores"):
            score -= .05 * len(_words(group, "generic_words"))
    return score


def select_composition_groups(
    groups: Iterable[Mapping[str, Any]], strategy: str | CompositionStrategy, limit: int
) -> list[dict[str, Any]]:
    """Replay a composition strategy without calling the production Gate."""
    strategy = CompositionStrategy(strategy)
    ranked = sorted((dict(group) for group in groups), key=lambda group: (-_offline_score(group, strategy), _group_id(group)))
    if limit <= 0:
        return []
    if strategy is CompositionStrategy.BASELINE or strategy is CompositionStrategy.GENERIC_WORD_DOWNWEIGHT:
        return ranked[:limit]
    selected: list[dict[str, Any]] = []
    remaining = ranked[:]
    while remaining and len(selected) < limit:
        if strategy is CompositionStrategy.DIRECT_MATCH_CAP:
            # Prefer a non-direct group once direct-only groups occupy half the
            # available slots. Direct groups are not removed from consideration.
            direct_count = sum(bool(_words(group, "direct_words")) for group in selected)
            pool = [group for group in remaining if not _words(group, "direct_words")] if direct_count >= max(1, limit // 2) else remaining
            choice = (pool or remaining)[0]
        else:
            seen_threads = set().union(*(_source_threads(group) for group in selected)) if selected else set()
            choice = min(remaining, key=lambda group: (bool(_source_threads(group) & seen_threads), -_offline_score(group, strategy), _group_id(group)))
        selected.append(choice)
        remaining.remove(choice)
    return selected


def replay_composition_strategies(
    groups: Iterable[Mapping[str, Any]], annotations: Mapping[str, str], limit: int,
    baseline_working_memory_words: Iterable[str] = (),
) -> dict[str, dict[str, Any]]:
    """Compare the four required strategies on the same captured group pool."""
    candidates = list(groups)
    expected = {word for word, label in annotations.items() if str(label).upper() == "SHOULD_RECALL"}
    prohibited = {word for word, label in annotations.items() if str(label).upper() == "SHOULD_NOT_RECALL"}
    known = expected | prohibited
    results: dict[str, dict[str, Any]] = {}
    for strategy in CompositionStrategy:
        selected = select_composition_groups(candidates, strategy, limit)
        recalled = set().union(*(_words(group) for group in selected)) if selected else set()
        results[strategy.value] = {
            "associative_target_recovery": len(recalled & expected),
            "should_not_recall_leakage": len(recalled & prohibited),
            "unexpected_recall": len(recalled - known),
            "selected_group_count": len(selected), "working_memory_size": len(recalled),
            "counterexample_count": len(expected - recalled),
            "selected_group_ids": [_group_id(group) for group in selected],
            "working_memory_size_delta": len(recalled) - len(set(baseline_working_memory_words)),
        }
    return results
