"""Read-only repeated Experience Thread storage diagnostics.

This module performs topology arithmetic against snapshots and Research Logger
records.  It never mutates the database and does not replay a deduplicated
recall topology.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import sqlite3
from statistics import mean
from typing import Any, Iterable, Mapping

from .path_growth import _pearson, thread_signature


STATE_FIELDS = (
    "canonical_key", "source_text", "created_by", "date", "created_at",
    "last_seen", "seen_count", "strength",
)
INTERVALS = ((1, 100), (101, 250), (251, 500), (501, 750), (751, 1000))


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _bucket(count: int) -> str:
    if count == 1:
        return "1"
    if count == 2:
        return "2"
    if count <= 4:
        return "3-4"
    if count <= 9:
        return "5-9"
    if count <= 19:
        return "10-19"
    if count <= 49:
        return "20-49"
    if count <= 99:
        return "50-99"
    return "100+"


def _path_bucket(count: int) -> str:
    if count == 1:
        return "1"
    if count <= 4:
        return "2-4"
    if count <= 9:
        return "5-9"
    if count <= 19:
        return "10-19"
    return "20+"


def _concentration(values: list[float]) -> dict[str, dict[str, float | int]]:
    ordered = sorted(values, reverse=True)
    total = sum(ordered)
    result: dict[str, dict[str, float | int]] = {}
    for percent in (1, 5, 10, 20):
        take = max(1, math.ceil(len(ordered) * percent / 100)) if ordered else 0
        result[f"top_{percent}_percent"] = {
            "producer_count": take,
            "share": sum(ordered[:take]) / total if total else 0.0,
        }
    return result


def _load_snapshot(db_path: Path) -> dict[str, Any]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(threads)")}
        selected = [field for field in ("thread_id", *STATE_FIELDS) if field in columns]
        threads = {
            str(row["thread_id"]): dict(row)
            for row in connection.execute(f"SELECT {', '.join(selected)} FROM threads")
        }
        words = {
            str(row["word_id"]): dict(row)
            for row in connection.execute(
                "SELECT word_id, word, seen_count, strength, weight FROM words"
            )
        }
        links = [
            dict(row)
            for row in connection.execute(
                "SELECT word_id, thread_id, weight_in_thread, added_at FROM word_threads"
            )
        ]

    thread_words: dict[str, set[str]] = defaultdict(set)
    word_threads: dict[str, set[str]] = defaultdict(set)
    thread_links: dict[str, list[dict[str, Any]]] = defaultdict(list)
    word_by_id = {word_id: str(row["word"]) for word_id, row in words.items()}
    for link in links:
        thread_id = str(link["thread_id"])
        word = word_by_id[str(link["word_id"])]
        thread_words[thread_id].add(word)
        word_threads[word].add(thread_id)
        thread_links[thread_id].append(link)

    signatures = {
        thread_id: thread_signature(thread_words[thread_id], row.get("created_by", ""))
        for thread_id, row in threads.items()
    }
    signature_threads: dict[str, list[str]] = defaultdict(list)
    wordset_threads: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for thread_id, signature in signatures.items():
        signature_threads[signature].append(thread_id)
        wordset_threads[tuple(sorted(thread_words[thread_id]))].append(thread_id)
    for member_ids in signature_threads.values():
        member_ids.sort(key=lambda thread_id: (
            str(threads[thread_id].get("created_at", "")), thread_id
        ))
    return {
        "threads": threads,
        "words": words,
        "links": links,
        "thread_words": thread_words,
        "word_threads": word_threads,
        "thread_links": thread_links,
        "signatures": signatures,
        "signature_threads": signature_threads,
        "wordset_threads": wordset_threads,
    }


def _state_equivalence(member_ids: list[str], threads: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    available = [field for field in STATE_FIELDS if all(field in threads[tid] for tid in member_ids)]
    if not available:
        return {"classification": "UNKNOWN_STATE_EQUIVALENCE", "compared_fields": [], "differing_fields": []}
    differing = [
        field for field in available
        if len({json.dumps(threads[tid].get(field), sort_keys=True, default=str) for tid in member_ids}) > 1
    ]
    return {
        "classification": (
            "STRUCTURALLY_DUPLICATE_BUT_STATE_DIFFERENT"
            if differing else "STRUCTURALLY_AND_STATE_EQUIVALENT"
        ),
        "compared_fields": available,
        "differing_fields": differing,
    }


def analyze_repeated_experience(
    records: Iterable[Mapping[str, Any]], db_path: Path
) -> dict[str, Any]:
    """Analyze one immutable logger/DB pair without changing either input."""
    rows = list(records)
    snapshot = _load_snapshot(db_path)
    threads = snapshot["threads"]
    signature_threads = snapshot["signature_threads"]
    signatures = snapshot["signatures"]
    word_threads = snapshot["word_threads"]

    thread_activity: dict[str, Counter[str]] = defaultdict(Counter)
    word_activity: dict[str, Counter[str]] = defaultdict(Counter)
    utility = Counter()
    candidate_observations: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        recall = row.get("recall", {}) if isinstance(row.get("recall"), dict) else {}
        evaluation = row.get("evaluation", {}) if isinstance(row.get("evaluation"), dict) else {}
        analysis = recall.get("activation_analysis", {}) if isinstance(recall.get("activation_analysis"), dict) else {}
        paths = [path for path in _as_list(analysis.get("paths")) if isinstance(path, dict)]
        candidates = [candidate for candidate in _as_list(analysis.get("candidates")) if isinstance(candidate, dict)]
        events = [event for event in _as_list(recall.get("stage_diagnostics")) if isinstance(event, dict)]
        selected = {str(word) for word in _as_list(recall.get("selected_words"))}
        expected = {str(word) for word in _as_list(evaluation.get("expected_words"))}
        unexpected = {str(word) for word in _as_list(evaluation.get("unexpected_words"))}

        for path in paths:
            contributing_threads = set()
            if path.get("from_type") == "thread":
                contributing_threads.add(str(path.get("from_id")))
            if path.get("to_type") == "thread":
                contributing_threads.add(str(path.get("to_id")))
            target_word = str(path.get("to_id")) if path.get("to_type") == "word" else ""
            for thread_id in contributing_threads:
                if thread_id not in signatures:
                    continue
                thread_activity[thread_id]["generated_paths"] += 1
                thread_activity[thread_id]["connections_traversed"] += 1
                if target_word in expected:
                    utility["expected_target_paths"] += 1
                    thread_activity[thread_id]["expected_target_paths"] += 1
                elif target_word in unexpected:
                    utility["unexpected_recall_paths"] += 1
                    thread_activity[thread_id]["unexpected_recall_paths"] += 1
                elif target_word and target_word not in selected:
                    utility["suppressed_candidate_paths"] += 1
                    thread_activity[thread_id]["suppressed_candidate_paths"] += 1
                else:
                    utility["unknown_paths"] += 1
                    thread_activity[thread_id]["unknown_paths"] += 1

        for rank, candidate in enumerate(candidates, start=1):
            word = str(candidate.get("word", ""))
            score = float(candidate.get("score", 0.0) or 0.0)
            gate_events = [
                event for event in events
                if event.get("stage") == "ACTIVATION_GATE" and str(event.get("identifier")) == word
            ]
            gate_selected = any(bool(event.get("accepted")) for event in gate_events)
            gate_suppressed = bool(gate_events) and not gate_selected
            admitted = word in selected
            word_activity[word]["activation_count"] += 1
            word_activity[word]["gate_selected"] += int(gate_selected)
            word_activity[word]["gate_suppressed"] += int(gate_suppressed)
            word_activity[word]["wm_admission"] += int(admitted)
            for signature in {signatures[thread_id] for thread_id in word_threads.get(word, set())}:
                candidate_observations[signature].append({
                    "score": score,
                    "rank": rank,
                    "gate_selected": gate_selected,
                    "wm_admitted": admitted,
                })

    signature_rows = []
    for signature, member_ids in signature_threads.items():
        words = sorted(snapshot["thread_words"][member_ids[0]])
        activity = sum((thread_activity[thread_id] for thread_id in member_ids), Counter())
        word_totals = sum((word_activity[word] for word in words), Counter())
        frequency = sum(
            int(row.get("seen_count", 0) or 0)
            for row in snapshot["words"].values() if str(row["word"]) in words
        )
        observations = candidate_observations.get(signature, [])
        created_values = [str(threads[tid].get("created_at", "")) for tid in member_ids if threads[tid].get("created_at")]
        state = _state_equivalence(member_ids, threads)
        signature_rows.append({
            "signature": signature,
            "repetition_count": len(member_ids),
            "first_observed_turn": None,
            "last_observed_turn": None,
            "turn_span": None,
            "temporal_status": "UNAVAILABLE_FROM_FINAL_SNAPSHOT",
            "first_observed_at": min(created_values, default=None),
            "last_observed_at": max(created_values, default=None),
            "created_by_distribution": dict(Counter(str(threads[tid].get("created_by", "")) for tid in member_ids)),
            "member_words": words,
            "connected_words": words,
            "frequency": frequency,
            "connection_count": sum(len(snapshot["thread_links"][tid]) for tid in member_ids),
            "generated_path_count": activity["generated_paths"],
            "connections_traversed_contribution": activity["connections_traversed"],
            "activation_count": word_totals["activation_count"],
            "gate_selected_count": word_totals["gate_selected"],
            "gate_suppressed_count": word_totals["gate_suppressed"],
            "wm_admission_count": word_totals["wm_admission"],
            "mean_candidate_score": mean([obs["score"] for obs in observations]) if observations else None,
            "mean_candidate_rank": mean([obs["rank"] for obs in observations]) if observations else None,
            "state_equivalence": state,
            "member_thread_ids": member_ids,
        })
    signature_rows.sort(key=lambda row: (-row["repetition_count"], row["signature"]))

    bucket_rows: dict[str, Counter[str]] = defaultdict(Counter)
    path_bucket_rows: dict[str, Counter[str]] = defaultdict(Counter)
    for signature_row in signature_rows:
        for target, bucket_name in ((bucket_rows, _bucket(signature_row["repetition_count"])), (path_bucket_rows, _path_bucket(signature_row["repetition_count"]))):
            aggregate = target[bucket_name]
            aggregate["signature_count"] += 1
            aggregate["thread_count"] += signature_row["repetition_count"]
            aggregate["connections"] += signature_row["connection_count"]
            aggregate["generated_paths"] += signature_row["generated_path_count"]
            aggregate["activation_contribution"] += signature_row["activation_count"]
            aggregate["gate_selected"] += signature_row["gate_selected_count"]
            aggregate["gate_suppressed"] += signature_row["gate_suppressed_count"]
            aggregate["wm_admission"] += signature_row["wm_admission_count"]

    total_threads = len(threads)
    unique_instances = len(signature_threads)
    repeat_instances = total_threads - unique_instances
    first_thread_ids = {member_ids[0] for member_ids in signature_threads.values()}
    unique_connections = sum(len(snapshot["thread_links"][tid]) for tid in first_thread_ids)
    repeat_connections = len(snapshot["links"]) - unique_connections
    unique_paths = sum(thread_activity[tid]["generated_paths"] for tid in first_thread_ids)
    total_thread_paths = sum(activity["generated_paths"] for activity in thread_activity.values())
    repeat_paths = total_thread_paths - unique_paths

    actual_fanout = {word: len(member_ids) for word, member_ids in word_threads.items()}
    first_only_fanout = {
        word: len({signatures[tid] for tid in member_ids})
        for word, member_ids in word_threads.items()
    }
    counterfactual_connections = unique_connections
    counterfactual = {
        "marker": "OFFLINE_TOPOLOGY_COUNTERFACTUAL",
        "production_replay": False,
        "recall_quality_assumption": "NONE",
        "threads_remaining": unique_instances,
        "threads_reduced": repeat_instances,
        "connections_remaining": counterfactual_connections,
        "connections_reduced": repeat_connections,
        "mean_word_fanout_before": mean(actual_fanout.values()) if actual_fanout else 0.0,
        "mean_word_fanout_first_instance_only": mean(first_only_fanout.values()) if first_only_fanout else 0.0,
        "estimated_traversable_connection_reduction": repeat_connections,
        "estimated_repeated_path_reduction": repeat_paths,
        "path_concentration_before": _concentration([row["generated_path_count"] for row in signature_rows]),
        "path_concentration_first_instance_only": _concentration([
            thread_activity[row["member_thread_ids"][0]]["generated_paths"] for row in signature_rows
        ]),
    }

    same_words_different_context = 0
    for member_ids in snapshot["wordset_threads"].values():
        contexts = {
            (str(threads[tid].get("created_by", "")), str(threads[tid].get("source_text", "")))
            for tid in member_ids
        }
        if len(contexts) > 1:
            same_words_different_context += len(member_ids)
    repeated_user = sum(
        row["repetition_count"] - 1 for row in signature_rows
        if row["repetition_count"] > 1 and set(row["created_by_distribution"]) == {"user"}
    )
    origin_classification = {
        "EXACT_REPEATED_EXPERIENCE": repeat_instances,
        "SAME_WORDS_DIFFERENT_CONTEXT": same_words_different_context,
        "REPEATED_USER_STATEMENT": repeated_user,
        "RECALL_DERIVED_REPETITION": 0,
        "UNKNOWN_REPETITION": repeat_instances - repeated_user,
        "recall_derived_status": "NOT_INFERRED_FROM_CREATED_BY_ALONE",
        "counts_are_non_exclusive": True,
    }

    state_counts = Counter(row["state_equivalence"]["classification"] for row in signature_rows if row["repetition_count"] > 1)
    reinforcement = Counter()
    multiplicity_rows = []
    for row in signature_rows:
        if row["repetition_count"] <= 1:
            continue
        member_states = [threads[tid] for tid in row["member_thread_ids"]]
        has_reinforcement = any(int(state.get("seen_count", 1) or 1) > 1 or float(state.get("strength", 1.0) or 1.0) > 1.0 for state in member_states)
        # A final snapshot proves the extra thread exists, but cannot attribute
        # word/thread reinforcement deltas to that individual repeat event.
        reinforcement["UNKNOWN"] += 1
        dimensions = ["thread_count", "path_multiplicity"]
        if row["frequency"] > len(row["member_words"]):
            dimensions.append("word_frequency")
        if has_reinforcement:
            dimensions.append("reinforcement_state")
        multiplicity_rows.append({"signature": row["signature"], "signal_dimensions": dimensions, "signal_count": len(dimensions)})
    reinforcement.update({"THREAD_ONLY": 0, "THREAD_AND_REINFORCEMENT": 0, "REINFORCEMENT_ONLY": 0, "NO_OBSERVABLE_CHANGE": 0})

    high_fanout = []
    for word in sorted(word_threads, key=lambda value: (-actual_fanout[value], value))[:20]:
        member_ids = word_threads[word]
        unique_count = len({signatures[tid] for tid in member_ids})
        repeated_count = len(member_ids) - unique_count
        high_fanout.append({
            "word": word,
            "connected_threads": len(member_ids),
            "unique_signatures": unique_count,
            "repeated_signature_instances": repeated_count,
            "unique_signature_ratio": unique_count / len(member_ids),
            "repeated_instance_ratio": repeated_count / len(member_ids),
        })

    correlation_rows = [row for row in signature_rows if row["mean_candidate_score"] is not None]
    correlations = {
        "repetition_vs_activation_score": _pearson([(row["repetition_count"], row["mean_candidate_score"]) for row in correlation_rows]),
        "repetition_vs_path_count": _pearson([(row["repetition_count"], row["generated_path_count"]) for row in signature_rows]),
        "repetition_vs_candidate_rank": _pearson([(row["repetition_count"], row["mean_candidate_rank"]) for row in correlation_rows]),
        "repetition_vs_gate_admission": _pearson([(row["repetition_count"], row["gate_selected_count"]) for row in signature_rows]),
    }

    known_utility = utility["expected_target_paths"] + utility["unexpected_recall_paths"]
    signature_utility = {
        "expected_target_contributing_signatures": [row["signature"] for row in signature_rows if any(thread_activity[tid]["expected_target_paths"] for tid in row["member_thread_ids"])],
        "unexpected_recall_contributing_signatures": [row["signature"] for row in signature_rows if any(thread_activity[tid]["unexpected_recall_paths"] for tid in row["member_thread_ids"])],
        "suppressed_only_signatures": [row["signature"] for row in signature_rows if any(thread_activity[tid]["suppressed_candidate_paths"] for tid in row["member_thread_ids"]) and not any(thread_activity[tid]["expected_target_paths"] or thread_activity[tid]["unexpected_recall_paths"] for tid in row["member_thread_ids"])],
    }
    signature_utility["unknown_signatures"] = [row["signature"] for row in signature_rows if row["signature"] not in set(signature_utility["expected_target_contributing_signatures"] + signature_utility["unexpected_recall_contributing_signatures"] + signature_utility["suppressed_only_signatures"])]
    utility_result = {
        **dict(utility),
        **signature_utility,
        "annotation_coverage": known_utility / max(sum(utility.values()), 1),
        "unknown_is_wasteful": False,
    }
    availability = {}
    for bucket_name, values in path_bucket_rows.items():
        activation = values["activation_contribution"]
        availability[bucket_name] = {
            **dict(values),
            "activation_rate_per_signature_ask": activation / max(values["signature_count"] * len(rows), 1),
            "gate_selection_rate": values["gate_selected"] / activation if activation else 0.0,
            "wm_admission_rate": values["wm_admission"] / activation if activation else 0.0,
        }
    storage_efficiency = {
        "unique_signatures_per_total_thread": unique_instances / total_threads if total_threads else 0.0,
        "repeat_instances_per_total_thread": repeat_instances / total_threads if total_threads else 0.0,
        "connections_per_unique_signature": len(snapshot["links"]) / unique_instances if unique_instances else None,
        "paths_per_unique_signature": total_thread_paths / unique_instances if unique_instances else None,
        "paths_per_total_thread": total_thread_paths / total_threads if total_threads else None,
        "quality_metric": False,
    }

    temporal = [{
        "turn_range": f"{start}-{end}",
        "new_unique_signatures": None,
        "new_repeated_instances": None,
        "cumulative_unique_signatures": None,
        "cumulative_repeated_instances": None,
        "status": "UNAVAILABLE_FROM_FINAL_SNAPSHOT",
    } for start, end in INTERVALS]

    return {
        "ask_count": len(rows),
        "repetition_origin_classification": origin_classification,
        "signature_count": unique_instances,
        "top_repeated_signatures": signature_rows[:30],
        "all_signature_statistics": signature_rows,
        "repetition_distribution": {key: dict(value) for key, value in sorted(bucket_rows.items())},
        "repetition_path_distribution": {key: dict(value) for key, value in sorted(path_bucket_rows.items())},
        "storage_contribution": {
            "total_threads": total_threads,
            "unique_first_instances": unique_instances,
            "exact_repeat_instances": repeat_instances,
            "repeat_storage_ratio": repeat_instances / total_threads if total_threads else 0.0,
            "total_connections": len(snapshot["links"]),
            "unique_first_instance_connections": unique_connections,
            "exact_repeat_instance_connections": repeat_connections,
            "repeat_connection_ratio": repeat_connections / len(snapshot["links"]) if snapshot["links"] else 0.0,
            "unique_first_instance_generated_paths": unique_paths,
            "exact_repeat_instance_generated_paths": repeat_paths,
            "repeat_generated_path_ratio": repeat_paths / total_thread_paths if total_thread_paths else 0.0,
        },
        "state_equivalence": dict(state_counts),
        "repetition_vs_reinforcement": dict(reinforcement),
        "repetition_signal_multiplicity": {
            "marker": "REPETITION_SIGNAL_MULTIPLICITY",
            "signature_count_with_three_or_more_signals": sum(row["signal_count"] >= 3 for row in multiplicity_rows),
            "signatures": multiplicity_rows,
            "bug_classification": False,
        },
        "repetition_relationships": correlations,
        "recall_utility": utility_result,
        "long_term_availability": {key: value for key, value in sorted(availability.items())},
        "temporal_accumulation": temporal,
        "duplicate_producers": signature_rows[:20],
        "high_fanout_repetition": high_fanout,
        "offline_first_instance_counterfactual": counterfactual,
        "storage_efficiency": storage_efficiency,
        "metadata_limits": {
            "turn_mapping": "UNAVAILABLE",
            "repeat_event_deltas": "UNAVAILABLE_FROM_FINAL_SNAPSHOT",
            "semantic_identity_added": False,
        },
    }


def compare_repeated_experience(short: Mapping[str, Any], long: Mapping[str, Any]) -> dict[str, Any]:
    short_storage = short["storage_contribution"]
    long_storage = long["storage_contribution"]
    metrics = {}
    for key in (
        "total_threads", "unique_first_instances", "exact_repeat_instances",
        "repeat_storage_ratio", "repeat_connection_ratio", "repeat_generated_path_ratio",
    ):
        before = short_storage[key]
        after = long_storage[key]
        metrics[key] = {
            "100_turn": before,
            "1000_turn": after,
            "raw_delta": after - before,
            "relative_delta": (after - before) / abs(before) if before else None,
        }

    state_different = long["state_equivalence"].get("STRUCTURALLY_DUPLICATE_BUT_STATE_DIFFERENT", 0)
    multiplicity = long["repetition_signal_multiplicity"]["signature_count_with_three_or_more_signals"]
    fanout_driven = long_storage["repeat_connection_ratio"] > 0.5
    repeat_pressure = long_storage["repeat_storage_ratio"] > 0.5
    factors = []
    if repeat_pressure and state_different:
        factors.append("STRUCTURAL_DUPLICATE_ACCUMULATION")
    if multiplicity:
        factors.append("REPETITION_SIGNAL_MULTIPLICITY")
    if fanout_driven:
        factors.append("REPEATED_EXPERIENCE_DRIVES_FANOUT")
    if not factors and long_storage["exact_repeat_instances"]:
        factors.append("BENIGN_REPEATED_EXPERIENCE")
    root_cause = factors[0] if len(factors) == 1 else "MIXED_REPETITION_PRESSURE" if factors else "INSUFFICIENT_EVIDENCE"
    recommendation = (
        "storage identityを研究する" if "STRUCTURAL_DUPLICATE_ACCUMULATION" in factors
        else "reinforcementとの二重計上を研究する" if "REPETITION_SIGNAL_MULTIPLICITY" in factors
        else "high-fanout nodeを研究する" if "REPEATED_EXPERIENCE_DRIVES_FANOUT" in factors
        else "offline deduplication experimentへ進む" if root_cause == "BENIGN_REPEATED_EXPERIENCE"
        else "3000-turn baselineへ進む"
    )
    return {
        "metric_comparison": metrics,
        "observed_factors": factors,
        "root_cause": root_cause,
        "next_recommended_step": recommendation,
        "production_change": False,
    }


def select_repetition_review_queue(analysis: Mapping[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    return [{
        "review_type": "TOP_EXACT_REPEAT_PRODUCER",
        "annotation_status": "REVIEW_REQUIRED",
        **{key: row.get(key) for key in (
            "signature", "member_words", "repetition_count", "first_observed_at",
            "last_observed_at", "frequency", "generated_path_count", "connection_count",
            "activation_count", "gate_suppressed_count", "wm_admission_count",
        )},
    } for row in analysis["duplicate_producers"][:limit]]


def repeated_experience_markdown(
    short: Mapping[str, Any], long: Mapping[str, Any], comparison: Mapping[str, Any]
) -> str:
    lines = [
        "# Repeated Experience Storage Analysis", "", "## Summary", "",
        "Read-only diagnosis of repeated Experience Thread storage. No deduplication or Production policy is implemented.",
    ]
    sections = (
        ("Repetition Distribution", "repetition_distribution"),
        ("Storage Contribution", "storage_contribution"),
        ("State Equivalence", "state_equivalence"),
        ("Repetition vs Reinforcement", "repetition_vs_reinforcement"),
        ("Signal Multiplicity", "repetition_signal_multiplicity"),
        ("Path Contribution", "repetition_path_distribution"),
        ("High-Fanout Relationship", "high_fanout_repetition"),
        ("Temporal Accumulation", "temporal_accumulation"),
        ("Recall Utility", "recall_utility"),
        ("Offline First-instance Counterfactual", "offline_first_instance_counterfactual"),
    )
    for title, key in sections:
        lines.extend(["", f"## {title}", "", f"100: `{json.dumps(short[key], ensure_ascii=False, sort_keys=True)}`", "", f"1000: `{json.dumps(long[key], ensure_ascii=False, sort_keys=True)}`"])
    lines.extend([
        "", "## Integrity Review", "",
        "Exact structural identity is distinct from state equivalence. Unknown provenance and temporal values remain UNKNOWN/UNAVAILABLE. The counterfactual is topology arithmetic, not a recall replay.",
        "", "## Root Cause", "", f"**{comparison['root_cause']}**", "",
        f"Observed factors: `{comparison['observed_factors']}`", "",
        "## Next Recommended Step", "", f"**{comparison['next_recommended_step']}**", "",
        "No deduplication, merge, pruning, threshold, schema, learning, recall, or reinforcement change was made.", "",
    ])
    return "\n".join(lines)
