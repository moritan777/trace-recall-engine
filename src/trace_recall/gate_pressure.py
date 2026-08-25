"""Offline Activation Gate pressure diagnostics over Research Logger v2."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from statistics import mean, median
from typing import Any, Iterable, Mapping


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _bucket_depth(value: int) -> str:
    return str(value) if value in {0, 1, 2} else "3+"


def _bucket_paths(value: int) -> str:
    return "1" if value <= 1 else "2-4" if value <= 4 else "5-9" if value <= 9 else "10-19" if value <= 19 else "20+"


def _bucket_frequency(value: int) -> str:
    return "0-2" if value <= 2 else "3-9" if value <= 9 else "10-49" if value <= 49 else "50-99" if value <= 99 else "100+"


def _source_type(candidate: Mapping[str, Any]) -> str:
    sources = {"DIRECT_INPUT" if str(value).startswith("input:") else "MUTUAL_AMPLIFICATION" if "mutual" in str(value).lower() else "THREAD_PROPAGATION" if str(value).startswith("thread:") else "OTHER" for value in _list(candidate.get("activation_sources"))}
    return next(iter(sources)) if len(sources) == 1 else "MULTI_SOURCE" if len(sources) > 1 else "OTHER"


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values); position = (len(ordered) - 1) * quantile; lower = math.floor(position); upper = math.ceil(position)
    return ordered[lower] if lower == upper else ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _pearson(pairs: list[tuple[float, float]]) -> dict[str, Any]:
    if len(pairs) < 30:
        return {"sample_count": len(pairs), "coefficient": None, "status": "INSUFFICIENT_SAMPLE"}
    xs = [pair[0] for pair in pairs]; ys = [pair[1] for pair in pairs]; mx = mean(xs); my = mean(ys)
    numerator = sum((x - mx) * (y - my) for x, y in pairs)
    denominator = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return {"sample_count": len(pairs), "coefficient": numerator / denominator if denominator else None, "status": "OBSERVED" if denominator else "NO_VARIANCE", "causal_interpretation": False}


def _candidate_state(identifier: str, events: list[Mapping[str, Any]]) -> tuple[bool, bool, str]:
    gate = next((event for event in events if event.get("stage") == "ACTIVATION_GATE" and str(event.get("identifier")) == identifier), None)
    wm = next((event for event in events if event.get("stage") == "WORKING_MEMORY" and str(event.get("identifier")) == identifier), None)
    return bool(gate and gate.get("accepted", True)), bool(wm and wm.get("accepted", True)), str(gate.get("reason", "UNOBSERVED")) if gate else "UNOBSERVED"


def analyze_gate_pressure(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(records); source = defaultdict(Counter); depth = defaultdict(Counter); path_buckets: dict[str, dict[str, Any]] = {}; frequency = defaultdict(Counter)
    scores = []; score_buckets = Counter(); suppression_causes = Counter(); asks = []; word_pressure = defaultdict(Counter)
    candidate_total = selected_total = wm_total = paths_total = threads_total = redundant = multi_thread = same_family = max_paths = 0
    useful = known_nonuseful = correctly_suppressed = labeled_candidates = 0
    timing_values = defaultdict(list)
    near_widths = []
    for row in rows:
        recall = row.get("recall", {}) if isinstance(row.get("recall"), dict) else {}; evaluation = row.get("evaluation", {}) if isinstance(row.get("evaluation"), dict) else {}
        analysis = recall.get("activation_analysis", {}) if isinstance(recall.get("activation_analysis"), dict) else {}
        candidates = [value for value in _list(analysis.get("candidates")) if isinstance(value, dict)]; paths = [value for value in _list(analysis.get("paths")) if isinstance(value, dict)]
        events = [value for value in _list(recall.get("stage_diagnostics")) if isinstance(value, dict)]
        expected = {str(value) for value in _list(evaluation.get("expected_words"))}; unexpected = {str(value) for value in _list(evaluation.get("unexpected_words"))}
        config = row.get("governance_observation_config", {}) if isinstance(row.get("governance_observation_config"), dict) else {}; threshold = float(config.get("gate_min_word_score", .05) or .05); near_width = max(threshold * .2, .01); near_widths.append(near_width)
        paths_by_word = defaultdict(list)
        for path in paths:
            if path.get("to_type") == "word": paths_by_word[str(path.get("to_id"))].append(path)
        active_threads = {str(path.get("from_id")) for path in paths if path.get("from_type") == "thread"} | {str(path.get("to_id")) for path in paths if path.get("to_type") == "thread"}
        threads_metadata = analysis.get("threads", {}) if isinstance(analysis.get("threads"), dict) else {}
        ask_selected = ask_wm = ask_suppressed = 0
        for candidate in candidates:
            identifier = str(candidate.get("word", "")); score = float(candidate.get("score", 0) or 0); candidate_paths = paths_by_word[identifier]; path_count = len(candidate_paths)
            max_paths = max(max_paths, path_count)
            gate_selected, admitted, reason = _candidate_state(identifier, events); ask_selected += gate_selected; ask_wm += admitted; ask_suppressed += int(not gate_selected)
            candidate_total += 1; selected_total += gate_selected; wm_total += admitted; paths_total += path_count; scores.append(score)
            source[_source_type(candidate)]["candidate_count"] += 1; source[_source_type(candidate)]["gate_selected"] += gate_selected; source[_source_type(candidate)]["gate_suppressed"] += int(not gate_selected); source[_source_type(candidate)]["working_memory_admitted"] += admitted
            depth_key = _bucket_depth(int(candidate.get("best_depth", 0) or 0)); depth[depth_key]["candidate_count"] += 1; depth[depth_key]["gate_selected"] += gate_selected; depth[depth_key]["gate_suppressed"] += int(not gate_selected); depth[depth_key]["working_memory_admitted"] += admitted
            path_key = _bucket_paths(path_count); bucket = path_buckets.setdefault(path_key, {"scores": [], "candidate_count": 0, "gate_selected": 0, "gate_suppressed": 0, "working_memory_admitted": 0}); bucket["scores"].append(score); bucket["candidate_count"] += 1; bucket["gate_selected"] += gate_selected; bucket["gate_suppressed"] += int(not gate_selected); bucket["working_memory_admitted"] += admitted
            frequency_value = int(candidate.get("frequency", 0) or 0); frequency_key = _bucket_frequency(frequency_value); frequency[frequency_key]["activation_count"] += 1; frequency[frequency_key]["gate_selected"] += gate_selected; frequency[frequency_key]["gate_suppressed"] += int(not gate_selected); frequency[frequency_key]["working_memory_admitted"] += admitted
            word_pressure[identifier]["activation_count"] += 1; word_pressure[identifier]["gate_suppressed"] += int(not gate_selected); word_pressure[identifier]["working_memory_admitted"] += admitted; word_pressure[identifier]["max_frequency"] = max(word_pressure[identifier]["max_frequency"], frequency_value)
            if score < threshold - near_width: score_buckets["far_below_threshold"] += 1
            elif score <= threshold + near_width: score_buckets["near_threshold"] += 1
            elif score <= threshold * 2: score_buckets["comfortably_above_threshold"] += 1
            else: score_buckets["very_high_score"] += 1
            if not gate_selected:
                suppression_causes["FATIGUE_RELATED" if reason == "recently_exposed" else "SCORE_INSUFFICIENT" if score < threshold else "UNCLASSIFIED"] += 1
            thread_ids = {str(path.get("from_id")) for path in candidate_paths if path.get("from_type") == "thread"}
            redundant += int(path_count > 1); multi_thread += int(len(thread_ids) > 1)
            families = [str(threads_metadata.get(thread_id, {}).get("canonical_key", "")) for thread_id in thread_ids if isinstance(threads_metadata.get(thread_id), dict)]
            same_family += int(len(families) > len(set(families)))
            labeled = identifier in expected or identifier in unexpected; labeled_candidates += labeled
            useful += int(identifier in expected and admitted); known_nonuseful += int(identifier in unexpected); correctly_suppressed += int(identifier in unexpected and not gate_selected)
        timing = row.get("timing", {}) if isinstance(row.get("timing"), dict) else {}
        for key in ("recall_ms", "llm_response_ms", "total_ms"):
            if timing.get(key) is not None: timing_values[key].append(float(timing[key] or 0))
        ask = {"turn": int(row.get("turn", 0) or 0), "candidate_count": len(candidates), "suppression_count": ask_suppressed, "selection_rate": ask_selected / len(candidates) if candidates else 0.0, "working_memory_admission_rate": ask_wm / len(candidates) if candidates else 0.0, "competition_density": len(candidates) / max(ask_wm, 1), "paths_per_candidate": len(paths) / max(len(candidates), 1), "connections_traversed": len(paths), "active_threads_touched": len(active_threads), "processing_time_ms": float(timing.get("total_ms", 0) or 0), "unexpected_recall": int(evaluation.get("unexpected_hit_count", 0) or 0), "abstention": int(not _list(recall.get("selected_words"))), "mean_frequency": mean([float(candidate.get("frequency", 0) or 0) for candidate in candidates]) if candidates else 0.0}
        asks.append(ask); threads_total += len(active_threads)
    for bucket in path_buckets.values():
        count = bucket["candidate_count"]; bucket["mean_score"] = mean(bucket.pop("scores")) if count else 0.0; bucket["gate_selection_rate"] = bucket["gate_selected"] / count if count else 0.0; bucket["suppression_rate"] = bucket["gate_suppressed"] / count if count else 0.0; bucket["working_memory_admission_rate"] = bucket["working_memory_admitted"] / count if count else 0.0
    score_distribution = {"mean": mean(scores) if scores else 0.0, "median": median(scores) if scores else 0.0, "p50": _percentile(scores, .5), "p75": _percentile(scores, .75), "p90": _percentile(scores, .9), "p95": _percentile(scores, .95), "max": max(scores, default=0.0)}
    top_turns = {}
    for label, key in (("TOP_CANDIDATE_PRESSURE", "candidate_count"), ("TOP_SUPPRESSION_PRESSURE", "suppression_count"), ("TOP_COMPETITION_PRESSURE", "competition_density"), ("TOP_LATENCY", "processing_time_ms")):
        top_turns[label] = sorted(asks, key=lambda value: (-value[key], value["turn"]))[:20]
    correlations = {name: _pearson([(float(row[left]), float(row[right])) for row in asks]) for name, left, right in (("candidate_count_vs_processing_time", "candidate_count", "processing_time_ms"), ("connection_traversals_vs_processing_time", "connections_traversed", "processing_time_ms"), ("competition_density_vs_unexpected_recall", "competition_density", "unexpected_recall"), ("competition_density_vs_abstention", "competition_density", "abstention"), ("frequency_vs_suppression", "mean_frequency", "suppression_count"), ("paths_per_candidate_vs_selection", "paths_per_candidate", "selection_rate"))}
    return {"ask_count": len(rows), "candidate_pressure": {"candidate_count": candidate_total, "candidate_per_ask": candidate_total / len(rows) if rows else 0.0, "gate_selected": selected_total, "gate_suppressed": candidate_total - selected_total, "selection_rate": selected_total / candidate_total if candidate_total else 0.0, "working_memory_admitted": wm_total, "working_memory_admission_rate": wm_total / candidate_total if candidate_total else 0.0}, "candidate_source_type": {key: dict(value) for key, value in sorted(source.items())}, "propagation_depth": {key: dict(value) for key, value in sorted(depth.items())}, "path_multiplicity": dict(sorted(path_buckets.items())), "path_pressure": {"active_threads_touched_per_ask": threads_total / len(rows) if rows else 0.0, "connections_traversed_per_ask": sum(row["connections_traversed"] for row in asks) / len(rows) if rows else 0.0, "mean_paths_per_candidate": paths_total / candidate_total if candidate_total else 0.0, "max_paths_per_candidate": max_paths}, "redundancy": {"duplicate_path_ratio": redundant / candidate_total if candidate_total else 0.0, "multi_thread_same_word_ratio": multi_thread / candidate_total if candidate_total else 0.0, "same_thread_family_ratio": same_family / candidate_total if candidate_total else 0.0, "candidate_redundancy_ratio": (redundant + multi_thread + same_family) / max(candidate_total * 3, 1)}, "score_distribution": score_distribution, "score_threshold_buckets": dict(score_buckets), "near_threshold_width": mean(near_widths) if near_widths else None, "suppression_causes": dict(suppression_causes), "frequency_pressure": {key: dict(value) for key, value in sorted(frequency.items())}, "high_frequency_low_admission_candidates": [{"word": word, **dict(values)} for word, values in sorted(word_pressure.items(), key=lambda item: (-item[1]["max_frequency"], item[1]["working_memory_admitted"], item[0]))[:20]], "value_classification": {"useful": useful, "wasteful": correctly_suppressed, "unknown": candidate_total - useful - correctly_suppressed, "gate_efficiency": useful / candidate_total if candidate_total else None, "gate_efficiency_coverage": labeled_candidates / candidate_total if candidate_total else 0.0, "suppression_efficiency": correctly_suppressed / known_nonuseful if known_nonuseful else None, "suppression_efficiency_coverage": known_nonuseful / candidate_total if candidate_total else 0.0}, "ask_pressure": asks, "top_pressure_turns": top_turns, "correlations": correlations, "latency": {key: {"mean": mean(values), "p95": _percentile(values, .95), "sample_count": len(values)} for key, values in timing_values.items()}, "unavailable_latency_stages": ["DB_LOOKUP", "ACTIVATION_TRAVERSAL", "GATE", "SELECTION", "WORKING_MEMORY", "DIAGNOSTICS_LOGGING"]}


def compare_gate_pressure(short: Mapping[str, Any], long: Mapping[str, Any]) -> dict[str, Any]:
    keys = (("candidate_per_ask", "candidate_pressure"), ("gate_suppressed", "candidate_pressure"), ("selection_rate", "candidate_pressure"), ("working_memory_admission_rate", "candidate_pressure"), ("active_threads_touched_per_ask", "path_pressure"), ("connections_traversed_per_ask", "path_pressure"), ("mean_paths_per_candidate", "path_pressure"), ("duplicate_path_ratio", "redundancy"), ("multi_thread_same_word_ratio", "redundancy"), ("candidate_redundancy_ratio", "redundancy"))
    comparison = {}
    for key, section in keys:
        before = float(short[section][key]); after = float(long[section][key]); comparison[key] = {"100_turn": before, "1000_turn": after, "raw_delta": after - before, "relative_delta": (after - before) / abs(before) if before else None}
    factors = []
    if comparison["mean_paths_per_candidate"]["raw_delta"] > 0 or comparison["connections_traversed_per_ask"]["raw_delta"] > 0: factors.append("PATH_EXPLOSION")
    short_high = sum(value.get("activation_count", 0) for key, value in short["frequency_pressure"].items() if key in {"50-99", "100+"}); long_high = sum(value.get("activation_count", 0) for key, value in long["frequency_pressure"].items() if key in {"50-99", "100+"})
    if long_high / max(long["ask_count"], 1) > short_high / max(short["ask_count"], 1): factors.append("FREQUENCY_PRESSURE")
    if comparison["candidate_redundancy_ratio"]["raw_delta"] > 0: factors.append("REDUNDANT_CANDIDATES")
    if comparison["selection_rate"]["raw_delta"] < 0 and comparison["candidate_per_ask"]["raw_delta"] > 0: factors.append("GATE_CAPACITY_PRESSURE")
    classification = factors[0] if len(factors) == 1 else "MIXED_PRESSURE" if factors else "INSUFFICIENT_EVIDENCE"
    recommendation = "path growthを研究する" if classification == "PATH_EXPLOSION" or classification == "MIXED_PRESSURE" and "PATH_EXPLOSION" in factors else "frequency pressureを研究する" if classification == "FREQUENCY_PRESSURE" else "candidate redundancyを研究する" if classification == "REDUNDANT_CANDIDATES" else "gate capacityを研究する" if classification == "GATE_CAPACITY_PRESSURE" else "3000-turnへ進む"
    return {"metric_comparison": comparison, "pressure_factors": factors, "root_cause": classification, "next_recommended_step": recommendation}


def select_pressure_review_turns(analysis: Mapping[str, Any], limit: int = 25) -> list[dict[str, Any]]:
    selected: dict[int, dict[str, Any]] = {}
    for category in ("TOP_CANDIDATE_PRESSURE", "TOP_SUPPRESSION_PRESSURE", "TOP_COMPETITION_PRESSURE", "TOP_LATENCY"):
        for row in analysis["top_pressure_turns"][category]:
            turn = int(row["turn"])
            selected.setdefault(turn, {"turn": turn, "expectation": "MAY_RECALL", "words": [], "benchmark_responsibility": "AMBIGUOUS", "coverage": [], "annotation_status": "REVIEW_REQUIRED"})
            if category not in selected[turn]["coverage"]: selected[turn]["coverage"].append(category)
    for row in analysis["ask_pressure"]:
        for condition, label in ((row["unexpected_recall"] > 0, "UNEXPECTED_RECALL"), (row["abstention"] > 0, "ABSTENTION")):
            if condition:
                turn = int(row["turn"]); selected.setdefault(turn, {"turn": turn, "expectation": "MAY_RECALL", "words": [], "benchmark_responsibility": "AMBIGUOUS", "coverage": [], "annotation_status": "REVIEW_REQUIRED"}); selected[turn]["coverage"].append(label)
    ranked = sorted(selected.values(), key=lambda row: (-len(set(row["coverage"])), row["turn"]))[:limit]
    for row in ranked: row["coverage"] = sorted(set(row["coverage"]))
    return sorted(ranked, key=lambda row: row["turn"])


def gate_pressure_markdown(short: Mapping[str, Any], long: Mapping[str, Any], comparison: Mapping[str, Any]) -> str:
    lines = ["# Activation Gate Pressure Analysis", "", "## Candidate Pressure", "", f"`{json.dumps(comparison['metric_comparison'], sort_keys=True)}`"]
    for heading, key in (("Path Pressure", "path_pressure"), ("Frequency Pressure", "frequency_pressure"), ("Redundancy", "redundancy"), ("Gate Suppression", "suppression_causes"), ("Latency", "latency"), ("Quality Relationship", "correlations")):
        lines.extend(["", f"## {heading}", "", f"100: `{json.dumps(short[key], ensure_ascii=False, sort_keys=True)}`", "", f"1000: `{json.dumps(long[key], ensure_ascii=False, sort_keys=True)}`"])
    lines.extend(["", "## Root Cause", "", f"**{comparison['root_cause']}**", "", f"Factors: `{comparison['pressure_factors']}`", "", "## Next Recommended Step", "", f"**{comparison['next_recommended_step']}**", "", "Correlations are observational, not causal. No production algorithm, threshold, or strategy was changed.", ""])
    return "\n".join(lines)
