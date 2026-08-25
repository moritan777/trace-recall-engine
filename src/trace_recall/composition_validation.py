"""Out-of-sample validation of the frozen Phase 2.9 composition rule."""

from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any, Iterable, Mapping

from .composition_features import analyze_composition_features, build_feature_table, threshold_scan


FROZEN_FEATURE = "generic_ratio"
FROZEN_THRESHOLD = 0.13636363636363635
STABILITY_FEATURES = (
    "generic_ratio", "mean_group_word_overlap", "mean_group_word_overlap_count",
    "source_thread_entropy", "score_entropy", "direct_match_concentration",
    "person_concentration",
)


def _apply_frozen_rule(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    predicted = [float(row["features"][FROZEN_FEATURE]) >= FROZEN_THRESHOLD for row in rows]
    actual = [row["outcome_class"] == "RECOVERY" for row in rows]
    tp = sum(p and a for p, a in zip(predicted, actual)); fp = sum(p and not a for p, a in zip(predicted, actual))
    fn = sum(not p and a for p, a in zip(predicted, actual)); tn = sum(not p and not a for p, a in zip(predicted, actual))
    positives = [row for row, selected in zip(rows, predicted) if selected]
    return {
        "feature": FROZEN_FEATURE, "threshold": FROZEN_THRESHOLD, "direction": ">=", "retrained": False,
        "precision": tp / (tp + fp) if tp + fp else 0.0, "recall": tp / (tp + fn) if tp + fn else 0.0,
        "false_positive": fp, "false_negative": fn,
        "balanced_accuracy": ((tp / (tp + fn) if tp + fn else 0.0) + (tn / (tn + fp) if tn + fp else 0.0)) / 2,
        "predicted_positive_count": len(positives), "true_recoveries": tp,
        "regressions": sum(row["outcome_class"] == "REGRESSION" for row in positives),
        "risky_recoveries": sum(row["recovery_safety"] == "RISKY_RECOVERY" for row in positives),
        "leakage_increases": sum(row["tradeoffs"]["leakage_increase"] for row in positives),
        "wm_growth_cases": sum(row["tradeoffs"]["wm_size_increase"] for row in positives),
    }


def _dataset_summary(rows: list[Mapping[str, Any]], table: list[Mapping[str, Any]]) -> dict[str, Any]:
    candidates = [len(row["candidate_groups"]) for row in rows]
    return {
        "scenario_count": len(rows), "candidate_count": {"min": min(candidates), "max": max(candidates), "mean": mean(candidates)},
        "shape_counts": dict(sorted(Counter(row.get("generation_metadata", {}).get("shape", "exploration") for row in rows).items())),
        "outcome_distribution": dict(Counter(row["outcome_class"] for row in table)),
        "recovery_safety_distribution": dict(Counter(row["recovery_safety"] for row in table if row["recovery_safety"] != "NOT_RECOVERY")),
    }


def validate_composition_signal(exploration: Iterable[Mapping[str, Any]], validation: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    exploration = list(exploration); validation = list(validation)
    exploration_analysis = analyze_composition_features(exploration)
    validation_table = build_feature_table(validation)
    # This is the primary validation. No threshold candidate is inspected here.
    frozen = _apply_frozen_rule(validation_table)
    validation_exploration = analyze_composition_features(validation)
    stability = {}
    reversals = 0
    for feature in STABILITY_FEATURES:
        old = exploration_analysis["feature_comparison"][feature]
        new = validation_exploration["feature_comparison"][feature]
        stable = old["effect_direction"] == new["effect_direction"]
        reversals += int(not stable and "LITTLE_DIFFERENCE" not in {old["effect_direction"], new["effect_direction"]})
        stability[feature] = {
            "exploration_recovery_mean": old["classes"]["RECOVERY"]["mean"], "exploration_regression_mean": old["classes"]["REGRESSION"]["mean"], "exploration_direction": old["effect_direction"],
            "validation_recovery_mean": new["classes"]["RECOVERY"]["mean"], "validation_regression_mean": new["classes"]["REGRESSION"]["mean"], "validation_direction": new["effect_direction"],
            "direction_maintained": stable,
        }
    fresh_rules = threshold_scan(validation_table)
    fresh = dict(fresh_rules[0]) if fresh_rules else None
    if fresh:
        fresh["scope"] = "exploratory only; fitted and measured on validation fixtures; not used for production or the generalization judgement"
    if frozen["balanced_accuracy"] < .55 or stability[FROZEN_FEATURE]["validation_direction"] == "REGRESSION_HIGHER":
        judgement = "SIGNAL_DID_NOT_GENERALIZE"
    elif frozen["precision"] < .7 or frozen["risky_recoveries"] or frozen["leakage_increases"] or frozen["wm_growth_cases"] > frozen["true_recoveries"] or reversals:
        judgement = "WEAKLY_GENERALIZED"
    else:
        judgement = "CONSISTENT_GENERALIZATION"
    next_step = "conditional composition研究へ進む" if judgement == "CONSISTENT_GENERALIZATION" else "validation datasetをさらに増やす" if judgement == "WEAKLY_GENERALIZED" else "composition研究を一旦止める"
    overall_tradeoffs = {
        "risky_recoveries": sum(row["recovery_safety"] == "RISKY_RECOVERY" for row in validation_table),
        "leakage_increases": sum(row["tradeoffs"]["leakage_increase"] for row in validation_table),
        "unexpected_recall_increases": sum(row["tradeoffs"]["unexpected_change"] > 0 for row in validation_table),
        "wm_growth_cases": sum(row["tradeoffs"]["wm_size_increase"] for row in validation_table),
        "new_counterexamples": sum(row["tradeoffs"]["new_counterexample"] for row in validation_table),
    }
    return {
        "exploration_dataset": _dataset_summary(exploration, exploration_analysis["feature_table"]),
        "validation_dataset": _dataset_summary(validation, validation_table),
        "frozen_rule_validation": frozen, "fresh_rule_exploration": fresh,
        "feature_effect_stability": stability,
        "rank_band_comparison": {"exploration": exploration_analysis["rank_band_analysis"], "validation": validation_exploration["rank_band_analysis"]},
        "validation_tradeoffs": overall_tradeoffs,
        "generalization_judgement": judgement, "next_recommended_step": next_step,
        "validation_feature_table": validation_table,
        "leakage_audit": {"frozen_threshold_retrained": False, "rank_used_as_feature": False, "coverage_used_as_feature": False, "target_or_label_used_as_feature": False},
        "warnings": ["Fresh validation-only threshold search is exploratory and in-sample.", "No strategy or production recall path was changed."],
    }


def composition_validation_markdown(result: Mapping[str, Any]) -> str:
    frozen = result["frozen_rule_validation"]
    lines = ["# Out-of-Sample Composition Validation", "", "The 30-scenario exploration dataset and independent validation dataset are evaluated without changing either dataset or any strategy.", "", "## Dataset Summary", "", f"- Exploration scenarios: {result['exploration_dataset']['scenario_count']}", f"- Validation scenarios: {result['validation_dataset']['scenario_count']}", f"- Validation shapes: `{result['validation_dataset']['shape_counts']}`", "", "## Frozen generic_ratio Rule", "", f"Rule: `generic_ratio >= {FROZEN_THRESHOLD}` (retrained: false)", "", f"- Precision: {frozen['precision']:.6f}", f"- Recall: {frozen['recall']:.6f}", f"- False positive / negative: {frozen['false_positive']} / {frozen['false_negative']}", f"- Balanced accuracy: {frozen['balanced_accuracy']:.6f}", f"- Risky recoveries: {frozen['risky_recoveries']}", f"- Leakage increases: {frozen['leakage_increases']}", f"- WM growth cases: {frozen['wm_growth_cases']}", "", "## Feature Effect Stability", "", "| Feature | Exploration direction | Validation direction | Maintained |", "|---|---|---|---|"]
    for feature, value in result["feature_effect_stability"].items():
        lines.append(f"| {feature} | {value['exploration_direction']} | {value['validation_direction']} | {value['direction_maintained']} |")
    lines.extend(["", "## Rank-band Comparison", "", f"- Exploration: `{result['rank_band_comparison']['exploration']}`", f"- Validation: `{result['rank_band_comparison']['validation']}`", "", "Rank is explanation-only and was not a classifier feature.", "", "## Validation Trade-offs", "", f"`{result['validation_tradeoffs']}`", "", "## Fresh Rule Exploration", "", f"`{result['fresh_rule_exploration']}`", "", "This rule is exploratory only and does not affect frozen-rule validation or production judgement.", "", "## Generalization Judgement", "", f"**{result['generalization_judgement']}**", "", "## Next Recommended Step", "", f"**{result['next_recommended_step']}**", "", "No conditional composition strategy or production implementation was started.", ""])
    return "\n".join(lines)
