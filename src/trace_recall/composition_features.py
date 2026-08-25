"""Target-blind, offline diagnostics for composition pre-selection features."""

from __future__ import annotations

from collections import Counter
import csv
from io import StringIO
import math
from statistics import mean, median
from typing import Any, Iterable, Mapping

from .composition_stress import evaluate_composition_stress


def _set(group: Mapping[str, Any], key: str) -> set[str]:
    value = group.get(key, [])
    return {str(item) for item in value} if isinstance(value, list) else set()


def _entropy(values: Iterable[float]) -> float:
    values = [float(value) for value in values if value > 0]
    total = sum(values)
    return -sum((value / total) * math.log2(value / total) for value in values) if total else 0.0


def _gini(values: Iterable[float]) -> float:
    ordered = sorted(max(0.0, float(value)) for value in values)
    total = sum(ordered)
    size = len(ordered)
    return sum((2 * index - size - 1) * value for index, value in enumerate(ordered, 1)) / (size * total) if size and total else 0.0


def _overlap(left: set[str], right: set[str]) -> tuple[int, float]:
    union = left | right
    return len(left & right), len(left & right) / len(union) if union else 0.0


def extract_preselection_features(candidate_groups: Iterable[Mapping[str, Any]], boundary: int) -> dict[str, float | int]:
    """Extract only candidate-pool data; no scenario, target, or label is accepted."""
    groups = sorted((dict(group) for group in candidate_groups), key=lambda group: (-float(group.get("group_score", group.get("score", 0.0)) or 0.0), str(group.get("canonical_key", ""))))
    scores = [float(group.get("group_score", group.get("score", 0.0)) or 0.0) for group in groups]
    top = groups[:4]
    top_scores = (scores + [0.0] * 4)[:4]
    score_total = sum(scores)
    word_counts: list[int] = []
    word_ratios: list[float] = []
    thread_counts: list[int] = []
    thread_ratios: list[float] = []
    for index, left in enumerate(top):
        for right in top[index + 1:]:
            count, ratio = _overlap(_set(left, "words"), _set(right, "words"))
            word_counts.append(count); word_ratios.append(ratio)
            count, ratio = _overlap(_set(left, "member_thread_ids"), _set(right, "member_thread_ids"))
            thread_counts.append(count); thread_ratios.append(ratio)
    direct_ratios = [len(_set(group, "direct_words")) / max(len(_set(group, "words")), 1) for group in groups]
    person_counts = [len(_set(group, "person_name_words")) for group in groups]
    generic_counts = [len(_set(group, "generic_words")) for group in groups]
    source_counts = [len(_set(group, "member_thread_ids")) for group in groups]
    source_threads = set().union(*(_set(group, "member_thread_ids") for group in groups)) if groups else set()
    signatures = {(tuple(sorted(_set(group, "words"))), tuple(sorted(_set(group, "member_thread_ids")))) for group in groups}
    near_duplicates = 0
    for index, left in enumerate(groups):
        for right in groups[index + 1:]:
            _, word_ratio = _overlap(_set(left, "words"), _set(right, "words"))
            _, thread_ratio = _overlap(_set(left, "member_thread_ids"), _set(right, "member_thread_ids"))
            near_duplicates += int(max(word_ratio, thread_ratio) >= .8)
    direct_total = sum(len(_set(group, "direct_words")) for group in groups)
    person_total = sum(person_counts)
    generic_total = sum(generic_counts)
    word_total = sum(len(_set(group, "words")) for group in groups)
    return {
        "top1_group_score": top_scores[0], "top2_group_score": top_scores[1], "top3_group_score": top_scores[2], "top4_group_score": top_scores[3],
        "top1_top2_gap": top_scores[0] - top_scores[1], "top2_top3_gap": top_scores[1] - top_scores[2], "top3_top4_gap": top_scores[2] - top_scores[3],
        "top1_share": top_scores[0] / score_total if score_total else 0.0, "top2_share": sum(top_scores[:2]) / score_total if score_total else 0.0,
        "score_entropy": _entropy(scores), "score_gini": _gini(scores),
        "mean_group_word_overlap": mean(word_ratios) if word_ratios else 0.0, "max_group_word_overlap": max(word_ratios, default=0.0),
        "mean_group_word_overlap_count": mean(word_counts) if word_counts else 0.0, "max_group_word_overlap_count": max(word_counts, default=0),
        "mean_thread_overlap": mean(thread_ratios) if thread_ratios else 0.0, "max_thread_overlap": max(thread_ratios, default=0.0),
        "mean_thread_overlap_count": mean(thread_counts) if thread_counts else 0.0, "max_thread_overlap_count": max(thread_counts, default=0),
        "top_group_direct_match_ratio": direct_ratios[0] if direct_ratios else 0.0, "mean_direct_match_ratio": mean(direct_ratios) if direct_ratios else 0.0,
        "max_direct_match_ratio": max(direct_ratios, default=0.0), "direct_match_concentration": max((len(_set(group, "direct_words")) for group in groups), default=0) / direct_total if direct_total else 0.0,
        "top_group_person_count": person_counts[0] if person_counts else 0, "mean_person_count": mean(person_counts) if person_counts else 0.0,
        "max_person_count": max(person_counts, default=0), "person_concentration": max(person_counts, default=0) / person_total if person_total else 0.0,
        "top_group_generic_count": generic_counts[0] if generic_counts else 0, "mean_generic_count": mean(generic_counts) if generic_counts else 0.0,
        "generic_ratio": generic_total / word_total if word_total else 0.0,
        "mean_distinct_source_threads": mean(source_counts) if source_counts else 0.0, "max_distinct_source_threads": max(source_counts, default=0),
        "total_unique_source_threads": len(source_threads), "source_thread_entropy": _entropy(source_counts),
        "unique_group_signature_count": len(signatures), "duplicate_or_near_duplicate_group_count": near_duplicates,
        "candidate_count": len(groups), "candidate_above_boundary_count": min(max(int(boundary), 0), len(groups)),
        "score_mass_top_n": sum(scores[:max(int(boundary), 0)]) / score_total if score_total else 0.0,
    }


def _rule_metrics(rows: list[Mapping[str, Any]], feature: str, threshold: float, direction: str) -> dict[str, Any]:
    predicted = [(float(row["features"][feature]) >= threshold) if direction == ">=" else (float(row["features"][feature]) <= threshold) for row in rows]
    actual = [row["outcome_class"] == "RECOVERY" for row in rows]
    tp = sum(p and a for p, a in zip(predicted, actual)); fp = sum(p and not a for p, a in zip(predicted, actual))
    fn = sum(not p and a for p, a in zip(predicted, actual)); tn = sum(not p and not a for p, a in zip(predicted, actual))
    positives = [row for row, value in zip(rows, predicted) if value]
    return {
        "feature": feature, "threshold": threshold, "direction": direction,
        "precision": tp / (tp + fp) if tp + fp else 0.0, "recall": tp / (tp + fn) if tp + fn else 0.0,
        "false_positive": fp, "false_negative": fn,
        "balanced_accuracy": ((tp / (tp + fn) if tp + fn else 0.0) + (tn / (tn + fp) if tn + fp else 0.0)) / 2,
        **_rule_safety(positives),
    }


def _rule_safety(rows: list[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "predicted_positive_count": len(rows), "true_recoveries": sum(row["outcome_class"] == "RECOVERY" for row in rows),
        "regressions": sum(row["outcome_class"] == "REGRESSION" for row in rows),
        "risky_recoveries": sum(row["recovery_safety"] == "RISKY_RECOVERY" for row in rows),
        "leakage_increases": sum(row["tradeoffs"]["leakage_increase"] for row in rows),
        "wm_growth_cases": sum(row["tradeoffs"]["wm_size_increase"] for row in rows),
    }


def threshold_scan(rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Scan observed values only; deterministic and intentionally non-ML."""
    rules = []
    feature_names = sorted(rows[0]["features"]) if rows else []
    for feature in feature_names:
        for threshold in sorted({float(row["features"][feature]) for row in rows}):
            for direction in (">=", "<="):
                rules.append(_rule_metrics(rows, feature, threshold, direction))
    return sorted(rules, key=lambda rule: (-rule["balanced_accuracy"], -rule["precision"], -rule["recall"], rule["feature"], rule["direction"], rule["threshold"]))


def _two_feature_scan(rows: list[Mapping[str, Any]], single_rules: list[Mapping[str, Any]]) -> dict[str, Any] | None:
    candidates = single_rules[:12]
    best = None
    for index, left in enumerate(candidates):
        for right in candidates[index + 1:]:
            if left["feature"] == right["feature"]:
                continue
            predicted = []
            for row in rows:
                first = float(row["features"][left["feature"]]) >= left["threshold"] if left["direction"] == ">=" else float(row["features"][left["feature"]]) <= left["threshold"]
                second = float(row["features"][right["feature"]]) >= right["threshold"] if right["direction"] == ">=" else float(row["features"][right["feature"]]) <= right["threshold"]
                predicted.append(first and second)
            actual = [row["outcome_class"] == "RECOVERY" for row in rows]
            tp = sum(p and a for p, a in zip(predicted, actual)); fp = sum(p and not a for p, a in zip(predicted, actual)); fn = sum(not p and a for p, a in zip(predicted, actual)); tn = sum(not p and not a for p, a in zip(predicted, actual))
            rule = {"conditions": [{key: left[key] for key in ("feature", "threshold", "direction")}, {key: right[key] for key in ("feature", "threshold", "direction")}], "precision": tp / (tp + fp) if tp + fp else 0.0, "recall": tp / (tp + fn) if tp + fn else 0.0, "false_positive": fp, "false_negative": fn, "balanced_accuracy": ((tp / (tp + fn) if tp + fn else 0.0) + (tn / (tn + fp) if tn + fp else 0.0)) / 2, **_rule_safety([row for row, value in zip(rows, predicted) if value])}
            key = (rule["balanced_accuracy"], rule["precision"], rule["recall"])
            if best is None or key > (best["balanced_accuracy"], best["precision"], best["recall"]):
                best = rule
    return best


def build_feature_table(scenarios: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Label outcomes after extracting features through the target-blind boundary."""
    scenarios = list(scenarios)
    stress = evaluate_composition_stress(scenarios)
    baseline = {row["scenario_id"]: row for row in stress["scenario_results"]["BASELINE"]}
    diversity = {row["scenario_id"]: row for row in stress["scenario_results"]["GROUP_DIVERSITY"]}
    table = []
    for scenario in scenarios:
        scenario_id = str(scenario["scenario_id"]); base = baseline[scenario_id]; changed = diversity[scenario_id]
        if not base["entered_working_memory"] and changed["entered_working_memory"]:
            outcome = "RECOVERY"
        elif base["entered_working_memory"] and not changed["entered_working_memory"]:
            outcome = "REGRESSION"
        else:
            outcome = "NO_TARGET_CHANGE"
        leakage = changed["should_not_recall_leakage"] > base["should_not_recall_leakage"]
        unexpected = changed["unexpected_recall"] - base["unexpected_recall"]
        safety = "RISKY_RECOVERY" if outcome == "RECOVERY" and (leakage or unexpected > 0) else "SAFE_RECOVERY" if outcome == "RECOVERY" else "NOT_RECOVERY"
        table.append({"scenario_id": scenario_id, "outcome_class": outcome, "recovery_safety": safety, "features": extract_preselection_features(scenario["candidate_groups"], int(scenario["group_limit"])), "tradeoffs": {"leakage_increase": leakage, "unexpected_change": unexpected, "wm_size_increase": changed["working_memory_size"] > base["working_memory_size"], "new_counterexample": outcome == "REGRESSION"}})
    return table


def analyze_composition_features(scenarios: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    scenarios = list(scenarios)
    table = build_feature_table(scenarios)
    classes = ("RECOVERY", "REGRESSION", "NO_TARGET_CHANGE")
    comparisons = {}
    for feature in sorted(table[0]["features"] if table else {}):
        by_class = {}
        for label in classes:
            values = [float(row["features"][feature]) for row in table if row["outcome_class"] == label]
            by_class[label] = {"mean": mean(values), "median": median(values), "min": min(values), "max": max(values), "count": len(values)} if values else None
        recovery_mean = by_class["RECOVERY"]["mean"] if by_class["RECOVERY"] else 0.0
        regression_mean = by_class["REGRESSION"]["mean"] if by_class["REGRESSION"] else 0.0
        direction = "RECOVERY_HIGHER" if recovery_mean > regression_mean and not math.isclose(recovery_mean, regression_mean) else "REGRESSION_HIGHER" if regression_mean > recovery_mean and not math.isclose(recovery_mean, regression_mean) else "LITTLE_DIFFERENCE"
        comparisons[feature] = {"classes": by_class, "effect_direction": direction, "recovery_regression_mean_difference": recovery_mean - regression_mean}
    rules = threshold_scan(table); best_single = rules[0] if rules else None
    best_two = _two_feature_scan(table, rules) if best_single and best_single["balanced_accuracy"] < .8 else None
    if best_two and best_two["balanced_accuracy"] <= best_single["balanced_accuracy"]:
        best_two = None
    family_counts: dict[str, Counter] = {}; rank_counts: dict[str, Counter] = {}
    rows_by_id = {row["scenario_id"]: row for row in table}
    for scenario in scenarios:
        outcome = rows_by_id[str(scenario["scenario_id"])]["outcome_class"]
        for tag in scenario["annotation"].get("coverage_tags", []):
            target = rank_counts if str(tag).startswith("rank_") else family_counts
            target.setdefault(str(tag), Counter())[outcome] += 1
    best_accuracy = best_two["balanced_accuracy"] if best_two and best_two["balanced_accuracy"] > best_single["balanced_accuracy"] else best_single["balanced_accuracy"] if best_single else 0.0
    judgement = "STRONG_RESEARCH_SIGNAL" if best_accuracy >= .8 and (best_two or best_single)["precision"] >= .7 else "WEAK_RESEARCH_SIGNAL" if best_accuracy >= .65 else "NO_USEFUL_SEPARATOR"
    next_step = "datasetを増やす" if judgement == "WEAK_RESEARCH_SIGNAL" else "conditional strategy研究へ進む" if judgement == "STRONG_RESEARCH_SIGNAL" else "composition研究を一旦止める"
    return {"scenario_count": len(table), "feature_names": sorted(table[0]["features"] if table else {}), "feature_table": table, "outcome_distribution": dict(Counter(row["outcome_class"] for row in table)), "recovery_safety_distribution": dict(Counter(row["recovery_safety"] for row in table if row["recovery_safety"] != "NOT_RECOVERY")), "feature_comparison": comparisons, "best_single_feature_rule": best_single, "best_two_feature_rule": best_two, "rank_band_analysis": {key: dict(value) for key, value in sorted(rank_counts.items())}, "scenario_family_analysis": {key: dict(value) for key, value in sorted(family_counts.items())}, "final_judgement": judgement, "next_recommended_step": next_step, "warnings": ["Thresholds were selected on only 30 in-sample fixtures and may be overfit.", "Offline separation signal is not a production policy."], "leakage_audit": {"classifier_feature_sources": ["candidate_groups", "group_limit"], "forbidden_inputs_excluded": ["expected_target", "expectation", "target_rank", "scenario_id", "coverage_tags"]}}


def feature_table_csv(result: Mapping[str, Any]) -> str:
    stream = StringIO(); fields = ["scenario_id", "outcome_class", "recovery_safety", *result["feature_names"]]
    writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
    for row in result["feature_table"]:
        writer.writerow({"scenario_id": row["scenario_id"], "outcome_class": row["outcome_class"], "recovery_safety": row["recovery_safety"], **row["features"]})
    return stream.getvalue()


def composition_feature_markdown(result: Mapping[str, Any]) -> str:
    lines = ["# Conditional Composition Feature Analysis", "", "Diagnostic offline analysis only. GROUP_DIVERSITY is not a production improvement; recovery is not necessarily safe; an offline separation signal is not a production policy.", "", "## Dataset", "", f"The existing {result['scenario_count']}-scenario composition stress dataset was used unchanged.", "", "## Feature Set", "", ", ".join(f"`{name}`" for name in result["feature_names"]), "", "## Target Leakage Audit", "", "Classifier features are extracted by a function that accepts only `candidate_groups` and `group_limit`. Expected target, expected label, target rank/group, scenario ID, and coverage tags are excluded.", "", "## Outcome Distribution", ""]
    for key in ("RECOVERY", "REGRESSION", "NO_TARGET_CHANGE"):
        lines.append(f"- {key}: {result['outcome_distribution'].get(key, 0)}")
    for key in ("SAFE_RECOVERY", "RISKY_RECOVERY"):
        lines.append(f"- {key}: {result['recovery_safety_distribution'].get(key, 0)}")
    strongest = sorted(result["feature_comparison"].items(), key=lambda item: (-abs(item[1]["recovery_regression_mean_difference"]), item[0]))[:10]
    lines.extend(["", "## Feature Comparison", "", "| Feature | RECOVERY mean | REGRESSION mean | Difference | Direction |", "|---|---:|---:|---:|---|"])
    for name, comparison in strongest:
        recovery = comparison["classes"]["RECOVERY"]["mean"]
        regression = comparison["classes"]["REGRESSION"]["mean"]
        lines.append(f"| {name} | {recovery:.6f} | {regression:.6f} | {comparison['recovery_regression_mean_difference']:.6f} | {comparison['effect_direction']} |")
    lines.extend(["", "Full mean, median, min, and max statistics for every feature/class are available in JSON.", "", "## Best Single-feature Rule", "", f"`{result['best_single_feature_rule']}`", ""])
    if result["best_two_feature_rule"]:
        lines.extend(["## Best Two-feature Rule", "", f"`{result['best_two_feature_rule']}`", ""])
    lines.extend(["## Rank-band Analysis", "", f"`{result['rank_band_analysis']}`", "", "## Scenario-family Analysis", "", f"`{result['scenario_family_analysis']}`", "", "## Trade-offs", "", f"Best-rule safety metadata: `{ {key: result['best_single_feature_rule'][key] for key in ('predicted_positive_count', 'true_recoveries', 'regressions', 'risky_recoveries', 'leakage_increases', 'wm_growth_cases')} }`", "", "## Final Judgement", "", f"**{result['final_judgement']}**", "", "## Next Recommended Step", "", f"**{result['next_recommended_step']}**", "", "The 30-scenario in-sample threshold scan is vulnerable to overfitting. No conditional strategy or production switch was implemented.", ""])
    return "\n".join(lines)
