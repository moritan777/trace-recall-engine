"""Evaluation of deterministic offline ThreadGroup composition fixtures."""

from __future__ import annotations

from collections import Counter
import json
from typing import Any, Iterable, Mapping

from .offline import CompositionStrategy, select_composition_groups


def _values(group: Mapping[str, Any], key: str, fallback: str | None = None) -> set[str]:
    value = group.get(key)
    if not isinstance(value, list) and fallback is not None:
        value = group.get(fallback)
    return {str(item) for item in value} if isinstance(value, list) else set()


def _scenario_strategy(row: Mapping[str, Any], strategy: CompositionStrategy) -> dict[str, Any]:
    annotation = row["annotation"]
    groups = row["candidate_groups"]
    selected = select_composition_groups(groups, strategy, int(row["group_limit"]))
    target = str(annotation["expected_target"])
    should_recall = annotation["expectation"] == "SHOULD_RECALL"
    group_words = set().union(*(_values(group, "words") for group in selected)) if selected else set()
    pre_fatigue = set().union(*(_values(group, "pre_fatigue_words", "words") for group in selected)) if selected else set()
    working_memory = set().union(*(_values(group, "working_memory_words", "pre_fatigue_words") for group in selected)) if selected else set()
    unexpected_words = {str(word) for word in annotation.get("unexpected_words", [])}
    group_included = target in group_words
    admitted = target in pre_fatigue
    final = target in working_memory
    return {
        "scenario_id": row["scenario_id"], "target": target,
        "group_included": group_included, "pre_fatigue_admitted": admitted,
        "entered_working_memory": final,
        "associative_target_recovery": int(should_recall and final),
        "should_not_recall_leakage": int(not should_recall and final),
        "unexpected_recall": len(working_memory & unexpected_words),
        "selected_group_count": len(selected), "working_memory_size": len(working_memory),
        "counterexample_count": int(should_recall and not final),
        "selected_group_ids": [str(group["canonical_key"]) for group in selected],
    }


def evaluate_composition_stress(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Compare unchanged offline strategies and make all regressions explicit."""
    scenarios = list(rows)
    details: dict[str, list[dict[str, Any]]] = {}
    summary: dict[str, dict[str, Any]] = {}
    for strategy in CompositionStrategy:
        outcomes = [_scenario_strategy(row, strategy) for row in scenarios]
        details[strategy.value] = outcomes
        should_count = sum(row["annotation"]["expectation"] == "SHOULD_RECALL" for row in scenarios)
        totals = Counter()
        for outcome in outcomes:
            for key in ("associative_target_recovery", "should_not_recall_leakage", "unexpected_recall", "selected_group_count", "working_memory_size", "counterexample_count"):
                totals[key] += outcome[key]
        totals.update({
            "group_inclusion_count": sum(outcome["group_included"] for outcome in outcomes),
            "pre_fatigue_admission_count": sum(outcome["pre_fatigue_admitted"] for outcome in outcomes),
            "final_working_memory_recall_count": sum(outcome["entered_working_memory"] for outcome in outcomes),
        })
        summary[strategy.value] = {
            **dict(totals),
            "group_inclusion_rate": totals["group_inclusion_count"] / len(scenarios) if scenarios else None,
            "pre_fatigue_admission_rate": totals["pre_fatigue_admission_count"] / len(scenarios) if scenarios else None,
            "final_working_memory_recall_rate": totals["associative_target_recovery"] / should_count if should_count else None,
            "average_selected_groups": totals["selected_group_count"] / len(scenarios) if scenarios else None,
            "average_working_memory_size": totals["working_memory_size"] / len(scenarios) if scenarios else None,
        }
    baseline = summary[CompositionStrategy.BASELINE.value]
    baseline_by_id = {outcome["scenario_id"]: outcome for outcome in details[CompositionStrategy.BASELINE.value]}
    tradeoffs = {}
    changed_scenarios: dict[str, list[dict[str, Any]]] = {}
    for strategy, metrics in summary.items():
        deltas = {key: metrics[key] - baseline[key] for key in ("associative_target_recovery", "should_not_recall_leakage", "unexpected_recall", "working_memory_size", "counterexample_count")}
        new_counterexamples = [
            outcome["scenario_id"] for outcome in details[strategy]
            if baseline_by_id[outcome["scenario_id"]]["entered_working_memory"] and not outcome["entered_working_memory"]
        ]
        newly_recovered = [
            outcome["scenario_id"] for outcome in details[strategy]
            if not baseline_by_id[outcome["scenario_id"]]["entered_working_memory"] and outcome["entered_working_memory"]
        ]
        tradeoffs[strategy] = {
            "deltas_vs_baseline": deltas,
            "leakage_increased": deltas["should_not_recall_leakage"] > 0,
            "unexpected_recall_increased": deltas["unexpected_recall"] > 0,
            "excessive_working_memory_growth": deltas["working_memory_size"] > max(2, baseline["working_memory_size"] * .2),
            "new_counterexample_count": len(new_counterexamples),
            "new_counterexample_scenarios": new_counterexamples,
            "newly_recovered_scenarios": newly_recovered,
            "counterexamples_increased": bool(new_counterexamples),
            "recovery_improved_with_tradeoff": bool(newly_recovered) and any((deltas["should_not_recall_leakage"] > 0, deltas["unexpected_recall"] > 0, deltas["working_memory_size"] > max(2, baseline["working_memory_size"] * .2), bool(new_counterexamples))),
        }
        rows_by_id = {str(row["scenario_id"]): row for row in scenarios}
        changes = []
        for outcome in details[strategy]:
            base = baseline_by_id[outcome["scenario_id"]]
            compared = ("entered_working_memory", "should_not_recall_leakage", "unexpected_recall", "selected_group_ids", "working_memory_size")
            if all(outcome[key] == base[key] for key in compared):
                continue
            source = rows_by_id[outcome["scenario_id"]]
            target_delta = int(outcome["entered_working_memory"]) - int(base["entered_working_memory"])
            leakage_delta = outcome["should_not_recall_leakage"] - base["should_not_recall_leakage"]
            unexpected_delta = outcome["unexpected_recall"] - base["unexpected_recall"]
            wm_delta = outcome["working_memory_size"] - base["working_memory_size"]
            labels = []
            if target_delta > 0:
                labels.append("IMPROVEMENT")
            elif target_delta < 0:
                labels.append("REGRESSION")
            if leakage_delta > 0:
                labels.append("LEAKAGE_INCREASE")
            if unexpected_delta > 0:
                labels.append("UNEXPECTED_RECALL_INCREASE")
            if wm_delta > 0 and target_delta == leakage_delta == unexpected_delta == 0:
                labels.append("WM_SIZE_ONLY_INCREASE")
            changes.append({
                "scenario_id": outcome["scenario_id"],
                "coverage_tags": source["annotation"].get("coverage_tags", []),
                "baseline_result": base, "strategy_result": outcome,
                "assessment": labels or ["COMPOSITION_CHANGED"],
                "target_rank_band": next((tag for tag in source["annotation"].get("coverage_tags", []) if str(tag).startswith("rank_")), "unknown"),
                "competition_shape": source.get("composition_features", {}).get("primary_condition", "unknown"),
            })
        changed_scenarios[strategy] = changes
    classifications = {}
    for strategy in CompositionStrategy:
        name = strategy.value
        comparison = tradeoffs[name]
        if name == CompositionStrategy.BASELINE.value or not comparison["newly_recovered_scenarios"] and not any((comparison["leakage_increased"], comparison["unexpected_recall_increased"], comparison["excessive_working_memory_growth"], comparison["counterexamples_increased"])):
            classification = "KEEP_BASELINE"
        elif comparison["newly_recovered_scenarios"] and not any((comparison["leakage_increased"], comparison["unexpected_recall_increased"], comparison["excessive_working_memory_growth"], comparison["counterexamples_increased"])):
            classification = "RESEARCH_CANDIDATE"
        else:
            classification = "REJECT"
        classifications[name] = classification
    coverage = Counter(tag for row in scenarios for tag in row["annotation"].get("coverage_tags", []))
    legacy = sum("legacy_turn_11_or_97_shape" in row["annotation"].get("coverage_tags", []) for row in scenarios)
    return {
        "scenario_count": len(scenarios), "coverage_counts": dict(sorted(coverage.items())),
        "non_legacy_shape_rate": (len(scenarios) - legacy) / len(scenarios) if scenarios else None,
        "strategy_summary": summary, "tradeoffs": tradeoffs, "scenario_results": details,
        "changed_scenarios": changed_scenarios, "classifications": classifications,
        "scope": "offline dataset replay only; production recall and the four offline strategies are unchanged",
    }


def composition_stress_markdown(result: Mapping[str, Any]) -> str:
    """Render aggregate results and every baseline-changing scenario."""
    metrics = result["strategy_summary"]
    tradeoffs = result["tradeoffs"]
    classifications = result["classifications"]
    lines = [
        "# Recall Composition Stress Evaluation", "",
        f"Scenarios: **{result['scenario_count']}**. Offline replay only; no production adoption is performed.", "",
        "## Strategy summary", "",
        "| Strategy | Recovery | SHOULD_NOT leakage | Unexpected recall | Group inclusion rate | Pre-fatigue admission rate | Final WM recall | Avg selected groups | Avg WM size | Aggregate counterexamples | New counterexamples | Recovered baseline failures | Classification |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for name in (strategy.value for strategy in CompositionStrategy):
        value = metrics[name]
        comparison = tradeoffs[name]
        lines.append(
            f"| {name} | {value['associative_target_recovery']} | {value['should_not_recall_leakage']} | {value['unexpected_recall']} | "
            f"{value['group_inclusion_rate']:.3f} | {value['pre_fatigue_admission_rate']:.3f} | {value['final_working_memory_recall_rate']:.3f} | "
            f"{value['average_selected_groups']:.3f} | {value['average_working_memory_size']:.3f} | {value['counterexample_count']} | "
            f"{comparison['new_counterexample_count']} | {len(comparison['newly_recovered_scenarios'])} | {classifications[name]} |"
        )
    lines.extend(["", "## Changed scenarios versus BASELINE", "", "Only scenarios whose target, leakage, unexpected recall, selected groups, or Working-Memory size changed are listed.", ""])
    for name in (strategy.value for strategy in CompositionStrategy if strategy is not CompositionStrategy.BASELINE):
        changes = result["changed_scenarios"][name]
        lines.extend([f"### {name}", "", f"Classification: **{classifications[name]}**", ""])
        if not changes:
            lines.extend(["No scenario changed from baseline.", ""])
            continue
        lines.extend(["| Scenario | Coverage tags | Baseline result | Strategy result | Improvement / regression | Target rank band | Competition shape |", "|---|---|---|---|---|---|---|"])
        for change in changes:
            base = _compact_result(change["baseline_result"])
            strategy_result = _compact_result(change["strategy_result"])
            lines.append(f"| {change['scenario_id']} | {', '.join(change['coverage_tags'])} | `{base}` | `{strategy_result}` | {', '.join(change['assessment'])} | {change['target_rank_band']} | {change['competition_shape']} |")
        lines.append("")
    lines.extend(["## Extracted trade-off cases", ""])
    extracts = {
        "Improved but broke another scenario": [name for name, value in tradeoffs.items() if value["newly_recovered_scenarios"] and value["new_counterexample_scenarios"]],
        "Leakage increased": [name for name, changes in result["changed_scenarios"].items() if any("LEAKAGE_INCREASE" in row["assessment"] for row in changes)],
        "Unexpected recall increased": [name for name, changes in result["changed_scenarios"].items() if any("UNEXPECTED_RECALL_INCREASE" in row["assessment"] for row in changes)],
        "WM size only increased": [name for name, changes in result["changed_scenarios"].items() if any("WM_SIZE_ONLY_INCREASE" in row["assessment"] for row in changes)],
    }
    for label, names in extracts.items():
        lines.append(f"- **{label}:** {', '.join(names) if names else 'none'}")
    lines.extend(["", "Classifications are offline research judgements only. Production strategies remain unchanged and unconnected.", ""])
    return "\n".join(lines)


def _compact_result(outcome: Mapping[str, Any]) -> str:
    value = {
        "target_in_wm": outcome["entered_working_memory"], "leakage": outcome["should_not_recall_leakage"],
        "unexpected": outcome["unexpected_recall"], "groups": outcome["selected_group_count"],
        "wm_size": outcome["working_memory_size"], "group_ids": outcome["selected_group_ids"],
    }
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
