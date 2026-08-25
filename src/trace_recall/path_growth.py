"""Read-only analysis of storage, fanout, and repeated path growth."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import json
import math
from pathlib import Path
import sqlite3
from statistics import mean, median
from typing import Any, Iterable, Mapping


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def thread_signature(words: Iterable[str], created_by: str = "") -> str:
    """Analysis-only exact signature; does not alter canonical storage keys."""
    return json.dumps({"created_by": str(created_by), "words": sorted({str(word) for word in words})}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _percentile(values: list[float], quantile: float) -> float:
    if not values: return 0.0
    ordered = sorted(values); position = (len(ordered) - 1) * quantile; low = math.floor(position); high = math.ceil(position)
    return ordered[low] if low == high else ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _distribution(values: list[float]) -> dict[str, float]:
    return {"mean": mean(values) if values else 0.0, "median": median(values) if values else 0.0, "p75": _percentile(values, .75), "p90": _percentile(values, .9), "p95": _percentile(values, .95), "max": max(values, default=0.0)}


def _pearson(pairs: list[tuple[float, float]]) -> dict[str, Any]:
    if len(pairs) < 30: return {"sample_count": len(pairs), "coefficient": None, "status": "INSUFFICIENT_SAMPLE", "causal_interpretation": False}
    xs = [pair[0] for pair in pairs]; ys = [pair[1] for pair in pairs]; mx = mean(xs); my = mean(ys); numerator = sum((x - mx) * (y - my) for x, y in pairs); denominator = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return {"sample_count": len(pairs), "coefficient": numerator / denominator if denominator else None, "status": "OBSERVED" if denominator else "NO_VARIANCE", "causal_interpretation": False}


def _load_storage(db_path: Path) -> dict[str, Any]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        threads = {str(row["thread_id"]): dict(row) for row in connection.execute("SELECT thread_id, canonical_key, created_by, created_at, seen_count FROM threads")}
        words = {str(row["word_id"]): dict(row) for row in connection.execute("SELECT word_id, word, seen_count FROM words")}
        links = [dict(row) for row in connection.execute("SELECT word_id, thread_id FROM word_threads")]
    thread_words = defaultdict(set); word_threads = defaultdict(set)
    for link in links:
        word = str(words[str(link["word_id"])]["word"]); thread_id = str(link["thread_id"]); thread_words[thread_id].add(word); word_threads[word].add(thread_id)
    signatures = {thread_id: thread_signature(thread_words[thread_id], row.get("created_by", "")) for thread_id, row in threads.items()}; counts = Counter(signatures.values())
    near_pairs = 0; thread_ids = sorted(threads)
    for index, left in enumerate(thread_ids):
        for right in thread_ids[index + 1:]:
            if signatures[left] == signatures[right]: continue
            union = thread_words[left] | thread_words[right]
            if union and len(thread_words[left] & thread_words[right]) / len(union) >= .8: near_pairs += 1
    per_word = [len(value) for value in word_threads.values()]; per_thread = [len(value) for value in thread_words.values()]
    repeated_threads = sum(value for value in counts.values() if value > 1)
    return {"threads": threads, "words": words, "links": links, "thread_words": thread_words, "word_threads": word_threads, "signatures": signatures, "signature_counts": counts, "thread_creation": {"total_experience_threads": len(threads), "unique_thread_signatures": len(counts), "exact_duplicate_thread_count": len(threads) - len(counts), "threads_in_repeated_signatures": repeated_threads, "repeated_signature_ratio": repeated_threads / len(threads) if threads else 0.0, "max_signature_repetition": max(counts.values(), default=0), "near_repeat_thread_pairs": near_pairs}, "connections": {"actual_connection_types": {"word_thread": len(links)}, "total_connections": len(links), "connections_per_word": _distribution([float(value) for value in per_word]), "connections_per_thread": _distribution([float(value) for value in per_thread])}}


def _fanout_bucket(value: int) -> str:
    return "1-4" if value <= 4 else "5-9" if value <= 9 else "10-19" if value <= 19 else "20-49" if value <= 49 else "50-99" if value <= 99 else "100+"


def analyze_path_origin(records: Iterable[Mapping[str, Any]], db_path: Path) -> dict[str, Any]:
    rows = list(records); storage = _load_storage(db_path); word_stats = defaultdict(Counter); thread_stats = defaultdict(Counter); asks = []; useful_paths = Counter(); path_types = Counter(); traversal_producers = Counter()
    expected_success = 0
    for row in rows:
        recall = row.get("recall", {}) if isinstance(row.get("recall"), dict) else {}; evaluation = row.get("evaluation", {}) if isinstance(row.get("evaluation"), dict) else {}; timing = row.get("timing", {}) if isinstance(row.get("timing"), dict) else {}
        analysis = recall.get("activation_analysis", {}) if isinstance(recall.get("activation_analysis"), dict) else {}; candidates = [value for value in _list(analysis.get("candidates")) if isinstance(value, dict)]; paths = [value for value in _list(analysis.get("paths")) if isinstance(value, dict)]; events = [value for value in _list(recall.get("stage_diagnostics")) if isinstance(value, dict)]
        expected = {str(value) for value in _list(evaluation.get("expected_words"))}; unexpected = {str(value) for value in _list(evaluation.get("unexpected_words"))}; selected = {str(value) for value in _list(recall.get("selected_words"))}; expected_success += int(evaluation.get("expected_hit_count", 0) or 0)
        active_threads = set(); word_path_counts = Counter()
        for path in paths:
            path_type = f"{path.get('from_type', 'other')}->{path.get('to_type', 'other')}"; path_types[path_type] += 1
            traversal_producers[f"{path.get('from_type', 'other')}:{path.get('from_id', '')}"] += 1
            if path.get("from_type") == "thread": active_threads.add(str(path.get("from_id"))); thread_stats[str(path.get("from_id"))]["generated_paths"] += 1
            if path.get("to_type") == "thread": active_threads.add(str(path.get("to_id"))); thread_stats[str(path.get("to_id"))]["generated_paths"] += 1
            if path.get("to_type") == "word":
                word = str(path.get("to_id")); word_path_counts[word] += 1; word_stats[word]["generated_paths"] += 1
                useful_paths["expected_target_paths" if word in expected else "unexpected_target_paths" if word in unexpected else "suppressed_candidate_paths" if word not in selected else "unknown_paths"] += 1
            else: useful_paths["unknown_paths"] += 1
        for candidate in candidates:
            word = str(candidate.get("word", "")); word_stats[word]["candidate_count"] += 1; word_stats[word]["activation_count"] += 1; word_stats[word]["max_frequency"] = max(word_stats[word]["max_frequency"], int(candidate.get("frequency", 0) or 0))
            gate = next((event for event in events if event.get("stage") == "ACTIVATION_GATE" and str(event.get("identifier")) == word), None); admitted = word in selected
            word_stats[word]["gate_selected"] += int(bool(gate and gate.get("accepted", True))); word_stats[word]["gate_suppressed"] += int(not bool(gate and gate.get("accepted", True))); word_stats[word]["working_memory_admitted"] += admitted
        asks.append({"turn": int(row.get("turn", 0) or 0), "threads_touched": len(active_threads), "connections_traversed": len(paths), "generated_word_paths": sum(word_path_counts.values()), "unique_candidates": len(candidates), "processing_time_ms": float(timing.get("total_ms", 0) or 0)})
    words = storage["words"]; word_threads = storage["word_threads"]; signatures = storage["signatures"]
    for word, thread_ids in word_threads.items():
        word_stats[word]["fanout"] = len(thread_ids); word_stats[word]["connection_count"] = len(thread_ids); word_stats[word]["frequency"] = int(next((value["seen_count"] for value in words.values() if value["word"] == word), 0)); unique_signatures = {signatures[thread_id] for thread_id in thread_ids}; word_stats[word]["unique_thread_signatures"] = len(unique_signatures); word_stats[word]["repeated_thread_signatures"] = len(thread_ids) - len(unique_signatures)
    fanout = defaultdict(Counter)
    for word, values in word_stats.items():
        bucket = fanout[_fanout_bucket(int(values["fanout"]))]; bucket["node_count"] += 1
        for key in ("activation_count", "generated_paths", "candidate_count", "gate_selected", "gate_suppressed", "working_memory_admitted"): bucket[key] += values[key]
    top_words = [{"identifier_type": "word", "word_identifier": word, **dict(values)} for word, values in sorted(word_stats.items(), key=lambda item: (-item[1]["fanout"], -item[1]["generated_paths"], item[0]))[:20]]
    same_word = [{"word": word, "contributing_threads": len(thread_ids), "unique_thread_signatures": word_stats[word]["unique_thread_signatures"], "repeated_thread_signatures": word_stats[word]["repeated_thread_signatures"], "paths_generated": word_stats[word]["generated_paths"], "frequency": word_stats[word]["frequency"]} for word, thread_ids in sorted(word_threads.items(), key=lambda item: (-len(item[1]), item[0]))]
    ordered_producers = sorted(traversal_producers.items(), key=lambda item: (-item[1], item[0])); total_produced = sum(traversal_producers.values())
    concentration = {}
    for percent in (1, 5, 10, 20):
        take = max(1, math.ceil(len(ordered_producers) * percent / 100)); share = sum(value for _, value in ordered_producers[:take]) / total_produced if total_produced else 0.0; concentration[f"top_{percent}_percent"] = {"producer_count": take, "connections_traversed_share": share, "generated_path_share": share}
    intervals = ((1, 100), (101, 250), (251, 500), (501, 750), (751, 1000)); historical = []
    for start, end in intervals:
        subset = [ask for ask in asks if start <= ask["turn"] <= end]
        historical.append({"turn_range": f"{start}-{end}", "ask_count": len(subset), "total_threads": None, "total_connections": None, "mean_fanout": None, "paths_per_ask": mean([ask["generated_word_paths"] for ask in subset]) if subset else None, "connections_traversed_per_ask": mean([ask["connections_traversed"] for ask in subset]) if subset else None, "candidates_per_ask": mean([ask["unique_candidates"] for ask in subset]) if subset else None, "processing_time_per_ask": mean([ask["processing_time_ms"] for ask in subset]) if subset else None})
    candidate_total = sum(ask["unique_candidates"] for ask in asks); traversed = sum(ask["connections_traversed"] for ask in asks); contributing = sum(ask["generated_word_paths"] for ask in asks); known_paths = useful_paths["expected_target_paths"] + useful_paths["unexpected_target_paths"] + useful_paths["suppressed_candidate_paths"]
    frequency_pairs = [(float(values["frequency"]), float(values["fanout"])) for values in word_stats.values()]; path_pairs = [(float(values["frequency"]), float(values["generated_paths"])) for values in word_stats.values()]
    created_at_pairs = []
    for thread_id, row in storage["threads"].items():
        try: created_at_pairs.append((datetime.fromisoformat(str(row.get("created_at", ""))).timestamp(), float(thread_stats[thread_id]["generated_paths"])))
        except (TypeError, ValueError): pass
    repetition = storage["thread_creation"]; reused = sum(int(row.get("seen_count", 1)) > 1 for row in storage["threads"].values())
    return {"ask_count": len(rows), "thread_creation": {**repetition, "threads_created_per_learn_turn": None, "learn_turn_count_status": "UNAVAILABLE_FROM_ASK_ONLY_RESEARCH_LOG"}, "connection_growth": {**storage["connections"], "traversed_path_types": dict(path_types)}, "high_fanout_nodes": top_words, "fanout_distribution": {key: dict(value) for key, value in sorted(fanout.items())}, "same_word_multi_thread": same_word, "repeated_experience": {"NEW_THREAD_ADDED": repetition["exact_duplicate_thread_count"], "THREAD_REUSED": reused, "CONNECTION_ONLY": "UNKNOWN", "REINFORCEMENT_ONLY": "UNKNOWN", "COMPOSITE": "UNKNOWN", "integrity_note": "shared-word fanout is not counted as an exact duplicate"}, "path_concentration": concentration, "historical_accumulation": historical, "historical_storage_snapshots": "UNAVAILABLE", "path_amplification": {"connections_traversed_per_candidate": traversed / candidate_total if candidate_total else 0.0, "contributing_paths_per_candidate": contributing / candidate_total if candidate_total else 0.0}, "useful_path_coverage": {**dict(useful_paths), "known_path_coverage": known_paths / max(traversed, 1)}, "storage_to_recall_efficiency": {"successful_expected_recalls": expected_success, "threads_per_successful_expected_recall": len(storage["threads"]) / expected_success if expected_success else None, "connections_per_successful_expected_recall": len(storage["links"]) / expected_success if expected_success else None, "traversed_paths_per_successful_expected_recall": traversed / expected_success if expected_success else None, "scope": "offline diagnostic; stable-fact responsibility is not added to the denominator"}, "frequency_relationship": {"frequency_vs_connected_threads": _pearson(frequency_pairs), "frequency_vs_connection_count": _pearson(frequency_pairs), "frequency_vs_generated_paths": _pearson(path_pairs)}, "age_relationship": _pearson(created_at_pairs) if created_at_pairs else {"status": "UNAVAILABLE", "causal_interpretation": False}, "performance_relationship": {"threads_touched": _pearson([(ask["threads_touched"], ask["processing_time_ms"]) for ask in asks]), "connections_traversed": _pearson([(ask["connections_traversed"], ask["processing_time_ms"]) for ask in asks]), "generated_paths": _pearson([(ask["generated_word_paths"], ask["processing_time_ms"]) for ask in asks]), "unique_candidates": _pearson([(ask["unique_candidates"], ask["processing_time_ms"]) for ask in asks])}, "top_path_producers": [{"identifier": identifier, "path_count": count, **({"frequency": word_stats[identifier[5:]]["frequency"], "fanout": word_stats[identifier[5:]]["fanout"], "candidate_count": word_stats[identifier[5:]]["candidate_count"], "selection_count": word_stats[identifier[5:]]["gate_selected"], "suppression_count": word_stats[identifier[5:]]["gate_suppressed"], "working_memory_admission_count": word_stats[identifier[5:]]["working_memory_admitted"]} if identifier.startswith("word:") else {"frequency": None, "fanout": len(storage["thread_words"].get(identifier[7:], set())), "candidate_count": None, "selection_count": None, "suppression_count": None, "working_memory_admission_count": None})} for identifier, count in ordered_producers[:20]], "ask_path_metrics": asks, "storage_metadata": {"db_path": str(db_path), "age_source": "threads.created_at", "historical_snapshot_limitation": "final DB has no turn-indexed storage snapshots"}}


def compare_path_origin(short: Mapping[str, Any], long: Mapping[str, Any]) -> dict[str, Any]:
    metrics = {"threads": (short["thread_creation"]["total_experience_threads"], long["thread_creation"]["total_experience_threads"]), "connections": (short["connection_growth"]["total_connections"], long["connection_growth"]["total_connections"]), "repeated_signature_ratio": (short["thread_creation"]["repeated_signature_ratio"], long["thread_creation"]["repeated_signature_ratio"]), "max_signature_repetition": (short["thread_creation"]["max_signature_repetition"], long["thread_creation"]["max_signature_repetition"]), "connections_per_thread": (short["connection_growth"]["total_connections"] / max(short["thread_creation"]["total_experience_threads"], 1), long["connection_growth"]["total_connections"] / max(long["thread_creation"]["total_experience_threads"], 1)), "path_amplification": (short["path_amplification"]["connections_traversed_per_candidate"], long["path_amplification"]["connections_traversed_per_candidate"]), "top_5_path_share": (short["path_concentration"]["top_5_percent"]["generated_path_share"], long["path_concentration"]["top_5_percent"]["generated_path_share"])}
    comparison = {key: {"100_turn": before, "1000_turn": after, "raw_delta": after - before, "relative_delta": (after - before) / abs(before) if before else None} for key, (before, after) in metrics.items()}
    factors = []
    if comparison["repeated_signature_ratio"]["raw_delta"] > 0: factors.append("REPEATED_EXPERIENCE_GROWTH")
    if comparison["top_5_path_share"]["raw_delta"] > 0: factors.append("HIGH_FANOUT_NODE_GROWTH")
    if comparison["path_amplification"]["raw_delta"] > 0 and comparison["connections_per_thread"]["raw_delta"] > 0: factors.append("CONNECTION_MULTIPLICATION")
    if comparison["threads"]["raw_delta"] > 0 and long["thread_creation"]["unique_thread_signatures"] / max(long["thread_creation"]["total_experience_threads"], 1) >= short["thread_creation"]["unique_thread_signatures"] / max(short["thread_creation"]["total_experience_threads"], 1): factors.append("BROAD_ORGANIC_MEMORY_GROWTH")
    classification = factors[0] if len(factors) == 1 else "MIXED_PATH_GROWTH" if factors else "INSUFFICIENT_EVIDENCE"
    if classification == "MIXED_PATH_GROWTH": recommendation = "repeated experience保存を研究する" if "REPEATED_EXPERIENCE_GROWTH" in factors else "connection生成を研究する"
    else: recommendation = "repeated experience保存を研究する" if classification == "REPEATED_EXPERIENCE_GROWTH" else "high-fanout nodeを研究する" if classification == "HIGH_FANOUT_NODE_GROWTH" else "connection生成を研究する" if classification == "CONNECTION_MULTIPLICATION" else "path traversal costを研究する" if classification == "BROAD_ORGANIC_MEMORY_GROWTH" else "3000-turn baselineへ進む"
    return {
        "metric_comparison": comparison,
        "growth_decomposition": {
            "STORAGE_GROWTH": {"unique_thread_signature_delta": long["thread_creation"]["unique_thread_signatures"] - short["thread_creation"]["unique_thread_signatures"]},
            "CONNECTION_FANOUT_GROWTH": {"top_5_path_share_delta": comparison["top_5_path_share"]["raw_delta"], "connections_per_thread_delta": comparison["connections_per_thread"]["raw_delta"]},
            "REPEATED_PATH_GROWTH": {"path_amplification_delta": comparison["path_amplification"]["raw_delta"], "repeated_signature_ratio_delta": comparison["repeated_signature_ratio"]["raw_delta"]},
        },
        "growth_factors": factors,
        "root_cause": classification,
        "next_recommended_step": recommendation,
    }


def select_path_review_queue(analysis: Mapping[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    return [{"identifier": row["identifier"], "review_type": "TOP_PATH_PRODUCER", "annotation_status": "REVIEW_REQUIRED", **{key: row.get(key) for key in ("frequency", "fanout", "path_count", "candidate_count", "selection_count", "suppression_count", "working_memory_admission_count")}} for row in analysis["top_path_producers"][:limit]]


def path_growth_markdown(short: Mapping[str, Any], long: Mapping[str, Any], comparison: Mapping[str, Any]) -> str:
    lines = ["# Path Growth Origin Analysis", "", "## Summary", "", "Read-only comparison of storage growth, connection fanout, and repeated paths under unchanged Production recall behavior."]
    for title, key in (("Thread Growth", "thread_creation"), ("Connection Growth", "connection_growth"), ("High-Fanout Nodes", "high_fanout_nodes"), ("Repeated Experience", "repeated_experience"), ("Same-word Multi-thread Growth", "same_word_multi_thread"), ("Path Concentration", "path_concentration"), ("Historical Growth", "historical_accumulation"), ("Path Amplification", "path_amplification"), ("Frequency Relationship", "frequency_relationship"), ("Performance Relationship", "performance_relationship")):
        lines.extend(["", f"## {title}", "", f"100: `{json.dumps(short[key], ensure_ascii=False, sort_keys=True)}`", "", f"1000: `{json.dumps(long[key], ensure_ascii=False, sort_keys=True)}`"])
    lines.extend(["", "## Integrity Review", "", "Exact deterministic thread signatures and shared-word fanout are reported separately. Shared concepts are not labeled duplicate memories.", "", "## Root Cause", "", f"**{comparison['root_cause']}**", "", f"Factors: `{comparison['growth_factors']}`", "", "## Next Recommended Step", "", f"**{comparison['next_recommended_step']}**", "", "No pruning, merging, retention, scoring, or production behavior was changed.", ""])
    return "\n".join(lines)
