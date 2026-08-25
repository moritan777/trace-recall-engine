"""Offline comparison of unchanged production-baseline research logs."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sqlite3
from statistics import mean
from typing import Any, Iterable, Mapping


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _db_stats(path: Path | None) -> dict[str, int | None]:
    if path is None or not path.exists():
        return {"word_node_count": None, "experience_thread_count": None, "connection_count": None, "db_size_bytes": None}
    with sqlite3.connect(path) as connection:
        values = {}
        for key, table in (("word_node_count", "words"), ("experience_thread_count", "threads"), ("connection_count", "word_threads")):
            values[key] = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    values["db_size_bytes"] = path.stat().st_size
    return values


def summarize_long_horizon(records: Iterable[Mapping[str, Any]], db_path: Path | None = None) -> dict[str, Any]:
    rows = list(records)
    precision = []; prompts = []; memories = []; groups = []; times = []
    unexpected = abstentions = fatigue_count = reentry_count = reentry_recovery = 0
    activated_total = suppressed_total = paths_total = selected_words_total = 0
    depths = []; competition = []; frequencies = []; roots = Counter(); fatigue_topics = Counter()
    frequency_relation: dict[int, Counter] = defaultdict(Counter)
    word_relation: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        recall = row.get("recall", {}) if isinstance(row.get("recall"), dict) else {}
        wm = row.get("working_memory", {}) if isinstance(row.get("working_memory"), dict) else {}
        evaluation = row.get("evaluation", {}) if isinstance(row.get("evaluation"), dict) else {}
        prompt = row.get("prompt", {}) if isinstance(row.get("prompt"), dict) else {}
        timing = row.get("timing", {}) if isinstance(row.get("timing"), dict) else {}
        selected = {str(word) for word in _list(recall.get("selected_words"))}
        activated = _list(recall.get("activated_words")); activated_total += len(activated)
        selected_words_total += len(selected); abstentions += int(not selected)
        unexpected += int(evaluation.get("unexpected_hit_count", 0) or 0)
        precision.append(float(evaluation.get("precision_like", 0.0) or 0.0))
        prompts.append(float(prompt.get("rough_tokens", 0) or 0)); memories.append(float(wm.get("word_count", 0) or 0)); groups.append(float(wm.get("thread_group_count", 0) or 0)); times.append(float(timing.get("total_ms", 0) or 0))
        reentry = {str(word) for word in _list(recall.get("topic_reentry_words"))}; reentry_count += int(bool(reentry)); reentry_recovery += int(bool(reentry & selected))
        analysis = recall.get("activation_analysis", {}) if isinstance(recall.get("activation_analysis"), dict) else {}
        candidates = [item for item in _list(analysis.get("candidates")) if isinstance(item, dict)]
        paths = [item for item in _list(analysis.get("paths")) if isinstance(item, dict)]
        paths_total += sum(str(path.get("to_id", "")) in selected for path in paths)
        depths.extend(float(item.get("best_depth", 0) or 0) for item in candidates)
        competition.append(len(candidates) / max(len(selected), 1))
        events = [event for event in _list(recall.get("stage_diagnostics")) if isinstance(event, dict)]
        first_rejection = {}
        raw_frequency = {}
        for event in events:
            identifier = str(event.get("identifier", "")); stage = str(event.get("stage", "UNKNOWN"))
            if stage == "RAW_ACTIVATION" and event.get("reason") == "raw activation candidate":
                frequency = int(event.get("raw_frequency", 0) or 0); raw_frequency[identifier] = frequency; frequencies.append(frequency); frequency_relation[frequency]["activated"] += 1
                word_relation[identifier]["activated"] += 1; word_relation[identifier]["max_raw_frequency"] = max(word_relation[identifier]["max_raw_frequency"], frequency)
            if not event.get("accepted", True) and identifier not in first_rejection:
                first_rejection[identifier] = stage; suppressed_total += 1; roots[stage] += 1
                if str(event.get("reason", "")) == "recently_exposed":
                    fatigue_count += 1; fatigue_topics[identifier] += 1
            if stage == "ACTIVATION_GATE" and event.get("accepted", True) and identifier in raw_frequency:
                frequency_relation[raw_frequency[identifier]]["gate_selected"] += 1
                word_relation[identifier]["gate_selected"] += 1
            if stage == "WORKING_MEMORY" and event.get("accepted", True) and identifier in raw_frequency:
                frequency_relation[raw_frequency[identifier]]["working_memory"] += 1
                word_relation[identifier]["working_memory"] += 1
    count = len(rows)
    ordered_times = sorted(times)
    p95 = ordered_times[min(len(ordered_times) - 1, max(0, int(len(ordered_times) * .95) - 1))] if ordered_times else 0.0
    result = {
        "ask_turn_count": count, "recall_precision": mean(precision) if precision else 0.0,
        "unexpected_recall": unexpected, "unexpected_recall_per_turn": unexpected / count if count else 0.0,
        "abstention_rate": abstentions / count if count else 0.0,
        "topic_fatigue_suppressions": fatigue_count, "unique_fatigued_topics": len(fatigue_topics),
        "repeated_fatigue_suppressions": sum(value - 1 for value in fatigue_topics.values() if value > 1),
        "topic_reentry_count": reentry_count, "explicit_reentry_recovery": reentry_recovery,
        "topic_reentry_recovery_rate": reentry_recovery / reentry_count if reentry_count else None,
        "pseudo_reentry_false_positive": None,
        "average_prompt_tokens": mean(prompts) if prompts else 0.0,
        "average_working_memory_words": mean(memories) if memories else 0.0,
        "average_thread_group_count": mean(groups) if groups else 0.0,
        "activation_candidate_count": activated_total, "average_activation_candidates": activated_total / count if count else 0.0,
        "candidate_suppression_count": suppressed_total, "average_candidate_suppressions": suppressed_total / count if count else 0.0,
        "stage_local_root_cause_failures": dict(sorted(roots.items())),
        "mean_raw_frequency": mean(frequencies) if frequencies else 0.0, "max_raw_frequency": max(frequencies, default=0),
        "contributing_paths_per_selected_word": paths_total / max(selected_words_total, 1),
        "average_propagation_depth": mean(depths) if depths else 0.0,
        "competition_density": mean(competition) if competition else 0.0,
        "total_evaluation_time_ms": sum(times), "average_turn_processing_ms": mean(times) if times else 0.0, "p95_turn_processing_ms": p95,
        "frequency_admission_relation": {str(key): dict(value) for key, value in sorted(frequency_relation.items())},
        "high_frequency_word_admission": [
            {"word": word, **dict(values)} for word, values in sorted(word_relation.items(), key=lambda item: (-item[1]["max_raw_frequency"], item[0]))[:20]
        ],
        "fatigued_topic_counts": dict(fatigue_topics.most_common()),
        **_db_stats(db_path),
    }
    return result


LOWER_IS_BETTER = {"unexpected_recall_per_turn", "abstention_rate", "average_prompt_tokens", "average_working_memory_words", "average_activation_candidates", "average_candidate_suppressions", "competition_density", "average_turn_processing_ms", "p95_turn_processing_ms"}
HIGHER_IS_BETTER = {"recall_precision", "topic_reentry_recovery_rate"}


def compare_long_horizon(short: Mapping[str, Any], long: Mapping[str, Any]) -> dict[str, Any]:
    metrics = sorted((LOWER_IS_BETTER | HIGHER_IS_BETTER) & short.keys() & long.keys())
    comparison = {}
    for metric in metrics:
        before = float(short[metric] or 0); after = float(long[metric] or 0); delta = after - before
        relative = delta / abs(before) if before else (0.0 if delta == 0 else None)
        if delta == 0:
            classification = "STABLE"
        elif (metric in HIGHER_IS_BETTER and delta > 0) or (metric in LOWER_IS_BETTER and delta < 0):
            classification = "IMPROVED"
        else:
            classification = "DEGRADED"
        comparison[metric] = {"100_turn": before, "1000_turn": after, "raw_delta": delta, "relative_delta": relative, "classification": classification}
    growth = {}
    for metric in ("word_node_count", "experience_thread_count", "connection_count", "activation_candidate_count", "average_prompt_tokens", "average_working_memory_words", "total_evaluation_time_ms", "db_size_bytes"):
        before = short.get(metric); after = long.get(metric)
        growth[metric] = {"100_turn": before, "1000_turn": after, "raw_delta": after - before if before is not None and after is not None else None, "relative_delta": (after - before) / abs(before) if before not in (None, 0) and after is not None else None}
    degraded = [key for key, value in comparison.items() if value["classification"] == "DEGRADED"]
    judgement = "SCALE_DEGRADATION_NEEDS_RESEARCH" if degraded else "BASELINE_SCALES_ACCEPTABLY" if short.get("ask_turn_count") and long.get("ask_turn_count") else "DATASET_INSUFFICIENT"
    return {"metric_comparison": comparison, "scale_growth": growth, "degraded_metrics": degraded, "final_judgement": judgement, "next_recommended_step": "最も悪化した1 subsystemだけ研究する" if degraded else "3000-turnへ進む" if judgement == "BASELINE_SCALES_ACCEPTABLY" else "annotationを増やす", "classification_policy": "zero-threshold sign comparison; raw and relative deltas are always retained"}


def select_annotation_turns(records: Iterable[Mapping[str, Any]], limit: int = 25) -> list[dict[str, Any]]:
    """Select representative observations; emits an overlay template, not labels."""
    rows = list(records); selected = {}; categories = defaultdict(list)
    for row in rows:
        recall = row.get("recall", {}); evaluation = row.get("evaluation", {})
        activated = len(_list(recall.get("activated_words"))); words = len(_list(recall.get("selected_words")))
        events = _list(recall.get("stage_diagnostics")); frequencies = [int(event.get("raw_frequency", 0) or 0) for event in events if isinstance(event, dict)]
        if activated >= 8: categories["high_activation_competition"].append(row)
        if int(evaluation.get("unexpected_hit_count", 0) or 0): categories["unexpected_recall"].append(row)
        if not words: categories["abstention"].append(row)
        if any(isinstance(event, dict) and ("fatigue" in str(event.get("reason", "")).lower() or event.get("fatigue_contribution")) for event in events): categories["fatigue_suppression"].append(row)
        if _list(recall.get("topic_reentry_words")): categories["explicit_reentry"].append(row)
        if max(frequencies, default=0) >= 10: categories["high_frequency_topic"].append(row)
        if words and frequencies and min(frequencies) <= 2: categories["low_frequency_successful_recall"].append(row)
    while len(selected) < min(limit, len(rows)):
        changed = False
        for category in sorted(categories):
            if len(selected) >= min(limit, len(rows)):
                break
            while categories[category]:
                row = categories[category].pop(0); turn = int(row.get("turn", 0) or 0)
                if turn not in selected:
                    selected[turn] = {"turn": turn, "expectation": "MAY_RECALL", "words": [], "benchmark_responsibility": "AMBIGUOUS", "coverage": [category], "annotation_status": "REVIEW_REQUIRED"}; changed = True; break
                if category not in selected[turn]["coverage"]: selected[turn]["coverage"].append(category)
        if not changed: break
    return [selected[key] for key in sorted(selected)]


def long_horizon_markdown(short: Mapping[str, Any], long: Mapping[str, Any], comparison: Mapping[str, Any]) -> str:
    lines = ["# Long-Horizon Production Baseline Validation", "", "## 100 vs 1000", "", "| Metric | 100-turn | 1000-turn | Raw delta | Relative delta | Classification |", "|---|---:|---:|---:|---:|---|"]
    for metric, value in comparison["metric_comparison"].items():
        relative = "N/A" if value["relative_delta"] is None else f"{value['relative_delta']:.6f}"
        lines.append(f"| {metric} | {value['100_turn']:.6f} | {value['1000_turn']:.6f} | {value['raw_delta']:.6f} | {relative} | {value['classification']} |")
    for heading, payload in (("Scale Growth", comparison["scale_growth"]), ("Recall Quality", {key: long[key] for key in ("recall_precision", "unexpected_recall", "abstention_rate")}), ("Activation Diffusion", {key: long[key] for key in ("average_activation_candidates", "contributing_paths_per_selected_word", "average_propagation_depth", "competition_density")}), ("Frequency Bias", {key: long[key] for key in ("mean_raw_frequency", "max_raw_frequency", "frequency_admission_relation", "high_frequency_word_admission")}), ("Topic Fatigue", {key: long[key] for key in ("topic_fatigue_suppressions", "unique_fatigued_topics", "repeated_fatigue_suppressions", "topic_reentry_count", "explicit_reentry_recovery", "pseudo_reentry_false_positive")}), ("Root Cause", long["stage_local_root_cause_failures"])):
        lines.extend(["", f"## {heading}", "", f"`{json.dumps(payload, ensure_ascii=False, sort_keys=True)}`"])
    lines.extend(["", "## Final Judgement", "", f"**{comparison['final_judgement']}**", "", "## Next Recommended Step", "", f"**{comparison['next_recommended_step']}**", "", "No production recall algorithm or offline composition strategy was changed or connected.", ""])
    return "\n".join(lines)
