"""Offline Experience Thread identity analysis.

The analysis compares possible identities using fields that already exist in the
SQLite snapshot.  It does not create a storage key or alter Production storage.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping

from .repeated_experience import _as_list, _load_snapshot


LEVEL_FIELDS = {
    "LEVEL_0_WORD_SET": ("word_set",),
    "LEVEL_1_SOURCE_TEXT": ("word_set", "source_text"),
    "LEVEL_2_ORIGIN": ("word_set", "source_text", "created_by"),
    "LEVEL_3_TEMPORAL_STATE": (
        "word_set", "source_text", "created_by", "date", "created_at", "last_seen",
    ),
    "LEVEL_4_STRENGTH_STATE": (
        "word_set", "source_text", "created_by", "date", "created_at", "last_seen",
        "seen_count", "strength",
    ),
}
OVER_SEPARATION_SINGLETON_RATIO = 0.95


def _identity_payload(thread_id: str, snapshot: Mapping[str, Any], level: str) -> tuple[Any, ...]:
    thread = snapshot["threads"][thread_id]
    values: list[Any] = []
    for field in LEVEL_FIELDS[level]:
        value: Any = tuple(sorted(snapshot["thread_words"][thread_id])) if field == "word_set" else thread.get(field)
        values.append(value)
    return tuple(values)


def _key(payload: tuple[Any, ...]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))


def _groups(snapshot: Mapping[str, Any], level: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for thread_id in snapshot["threads"]:
        result[_key(_identity_payload(thread_id, snapshot, level))].append(thread_id)
    for members in result.values():
        members.sort(key=lambda thread_id: (
            str(snapshot["threads"][thread_id].get("created_at", "")), thread_id
        ))
    return dict(result)


def _level_metrics(groups: Mapping[str, list[str]], total: int) -> dict[str, Any]:
    repetitions = [len(members) for members in groups.values()]
    repeat_instances = total - len(groups)
    singleton_count = sum(count == 1 for count in repetitions)
    singleton_ratio = singleton_count / len(groups) if groups else 0.0
    return {
        "unique_identity_count": len(groups),
        "repeat_instance_count": repeat_instances,
        "repeat_ratio": repeat_instances / total if total else 0.0,
        "max_repetition": max(repetitions, default=0),
        "mean_repetition": mean(repetitions) if repetitions else 0.0,
        "unique_ratio": len(groups) / total if total else 0.0,
        "singleton_ratio": singleton_ratio,
        "over_separating": singleton_ratio >= OVER_SEPARATION_SINGLETON_RATIO,
        "over_separation_threshold": OVER_SEPARATION_SINGLETON_RATIO,
    }


def _difference_class(differences: set[str]) -> str:
    if not differences:
        return "NO_OBSERVED_DIFFERENCE"
    content = bool(differences & {"source_text"})
    origin = bool(differences & {"created_by"})
    temporal = bool(differences & {"date", "created_at"})
    state = bool(differences) and differences <= {"last_seen", "seen_count", "strength"}
    categories = sum((content, origin, temporal, state))
    if state:
        return "STATE_ONLY_DIFFERENCE"
    if categories > 1 or differences & {"last_seen", "seen_count", "strength"}:
        return "MIXED_DIFFERENCE"
    if content:
        return "CONTENT_DIFFERENCE"
    if origin:
        return "ORIGIN_DIFFERENCE"
    if temporal:
        return "TEMPORAL_DIFFERENCE"
    return "STATE_ONLY_DIFFERENCE"


def _connection_equivalence(members: list[str], snapshot: Mapping[str, Any]) -> str:
    sets = [set(snapshot["thread_words"][thread_id]) for thread_id in members]
    if len({tuple(sorted(values)) for values in sets}) == 1:
        return "IDENTICAL_CONNECTION_SET"
    if any(left & right for index, left in enumerate(sets) for right in sets[index + 1:]):
        return "PARTIAL_CONNECTION_SET"
    return "DIFFERENT_CONNECTION_SET"


def _model_topology(
    snapshot: Mapping[str, Any], groups: Mapping[str, list[str]],
    thread_activity: Mapping[str, Counter[str]], model: str,
) -> dict[str, Any]:
    representatives = [members[0] for members in groups.values()]
    identities = len(groups)
    total = len(snapshot["threads"])
    connections = sum(len(snapshot["thread_links"][thread_id]) for thread_id in representatives)
    path_opportunities = sum(thread_activity[thread_id]["generated_paths"] for thread_id in representatives)
    per_word: dict[str, set[str]] = defaultdict(set)
    for identity, members in groups.items():
        for thread_id in members:
            for word in snapshot["thread_words"][thread_id]:
                per_word[word].add(identity)
    return {
        "model": model,
        "marker": "OFFLINE_IDENTITY_COUNTERFACTUAL",
        "production_replay": False,
        "recall_quality_assumption": "NONE",
        "estimated_thread_identities": identities,
        "estimated_repeat_state_updates": total - identities,
        "estimated_connections": connections,
        "estimated_connection_traversal_opportunities": connections,
        "estimated_observed_path_opportunities": path_opportunities,
        "estimated_repeated_path_opportunities": sum(activity["generated_paths"] for activity in thread_activity.values()) - path_opportunities,
        "mean_fanout": mean([len(identities_for_word) for identities_for_word in per_word.values()]) if per_word else 0.0,
        "high_fanout": [
            {"word": word, "connected_identities": len(identities_for_word)}
            for word, identities_for_word in sorted(per_word.items(), key=lambda item: (-len(item[1]), item[0]))[:20]
        ],
    }


def analyze_storage_identity(
    records: Iterable[Mapping[str, Any]], db_path: Path
) -> dict[str, Any]:
    """Analyze existing identity fields without target inference or mutation."""
    rows = list(records)
    snapshot = _load_snapshot(db_path)
    thread_ids = sorted(snapshot["threads"])
    total = len(thread_ids)
    level_groups = {level: _groups(snapshot, level) for level in LEVEL_FIELDS}

    identity_levels: dict[str, dict[str, Any]] = {}
    previous_repeats: int | None = None
    for level in LEVEL_FIELDS:
        metrics = _level_metrics(level_groups[level], total)
        repeats = metrics["repeat_instance_count"]
        metrics["identity_information_gain"] = (
            None if previous_repeats is None else
            (previous_repeats - repeats) / previous_repeats if previous_repeats else 0.0
        )
        identity_levels[level] = metrics
        previous_repeats = repeats

    level_zero_groups = level_groups["LEVEL_0_WORD_SET"]
    split_matrix = []
    difference_fields = ("source_text", "created_by", "date", "created_at", "last_seen", "seen_count", "strength")
    state_difference_causes = Counter({field: 0 for field in difference_fields})
    state_bearing = Counter({label: 0 for label in (
        "STATE_ONLY_DIFFERENCE", "CONTENT_DIFFERENCE", "ORIGIN_DIFFERENCE",
        "TEMPORAL_DIFFERENCE", "MIXED_DIFFERENCE", "NO_OBSERVED_DIFFERENCE",
    )})
    source_variations = []
    experience_classification = Counter()
    connection_equivalence = Counter({label: 0 for label in (
        "IDENTICAL_CONNECTION_SET", "PARTIAL_CONNECTION_SET", "DIFFERENT_CONNECTION_SET",
    )})
    for level_zero_identity, members in level_zero_groups.items():
        if len(members) <= 1:
            continue
        differences = {
            field for field in difference_fields
            if len({json.dumps(snapshot["threads"][thread_id].get(field), sort_keys=True, default=str) for thread_id in members}) > 1
        }
        state_difference_causes.update(differences)
        difference_class = _difference_class(differences)
        state_bearing[difference_class] += 1
        connection_equivalence[_connection_equivalence(members, snapshot)] += 1

        identities_by_level = {
            level: len({_key(_identity_payload(thread_id, snapshot, level)) for thread_id in members})
            for level in LEVEL_FIELDS
        }
        split_matrix.append({
            "level_0_identity": level_zero_identity,
            "member_words": sorted(snapshot["thread_words"][members[0]]),
            "level_0_instances": len(members),
            "level_1_identities": identities_by_level["LEVEL_1_SOURCE_TEXT"],
            "level_2_identities": identities_by_level["LEVEL_2_ORIGIN"],
            "level_3_identities": identities_by_level["LEVEL_3_TEMPORAL_STATE"],
            "level_4_identities": identities_by_level["LEVEL_4_STRENGTH_STATE"],
            "difference_fields": sorted(differences),
            "difference_classification": difference_class,
            "connection_set_equivalence": _connection_equivalence(members, snapshot),
        })

        sources = {str(snapshot["threads"][thread_id].get("source_text", "")) for thread_id in members}
        origins = {str(snapshot["threads"][thread_id].get("created_by", "")) for thread_id in members}
        temporal = {(snapshot["threads"][thread_id].get("date"), snapshot["threads"][thread_id].get("created_at")) for thread_id in members}
        strength = {(snapshot["threads"][thread_id].get("seen_count"), snapshot["threads"][thread_id].get("strength")) for thread_id in members}
        if len(sources) > 1:
            source_variations.append({
                "level_0_identity": level_zero_identity,
                "instance_count": len(members),
                "unique_source_text_count": len(sources),
                "source_text_examples": sorted(sources)[:5],
                "created_by": sorted(origins),
                "date_time_state": sorted((str(date), str(created)) for date, created in temporal)[:5],
                "strength_state": sorted((str(seen), str(value)) for seen, value in strength),
            })

        level_one_count = identities_by_level["LEVEL_1_SOURCE_TEXT"]
        level_three_count = identities_by_level["LEVEL_3_TEMPORAL_STATE"]
        level_four_count = identities_by_level["LEVEL_4_STRENGTH_STATE"]
        if level_three_count == 1 and level_four_count > 1:
            experience_classification["STATE_UPDATE_LIKE"] += 1
        elif level_one_count == 1:
            experience_classification["REPEATED_DESCRIPTION"] += 1
        else:
            experience_classification["UNRESOLVABLE"] += 1
    split_matrix.sort(key=lambda row: (-row["level_0_instances"], row["level_0_identity"]))
    source_variations.sort(key=lambda row: (-row["instance_count"], row["level_0_identity"]))
    for label in ("SAME_RECORDED_EVENT", "REPEATED_DESCRIPTION", "DISTINCT_TEMPORAL_EVENT", "STATE_UPDATE_LIKE", "UNRESOLVABLE"):
        experience_classification[label] += 0

    temporal_gain = identity_levels["LEVEL_3_TEMPORAL_STATE"]["identity_information_gain"] or 0.0
    timestamp_artifact = (
        temporal_gain > 0
        and state_difference_causes["created_at"] > 0
        and identity_levels["LEVEL_2_ORIGIN"]["unique_identity_count"]
            == identity_levels["LEVEL_1_SOURCE_TEXT"]["unique_identity_count"]
    )
    temporal_review = {
        "date_semantics": "STORAGE_DATE_DERIVED_FROM_NOW",
        "created_at_semantics": "STORAGE_TIMESTAMP",
        "last_seen_semantics": "MUTABLE_LAST_OBSERVATION_TIMESTAMP",
        "timestamp_uniqueness_artifact": timestamp_artifact,
        "classification": "TIMESTAMP_UNIQUENESS_ARTIFACT" if timestamp_artifact else "NOT_OBSERVED",
        "warning": "Timestamp uniqueness does not establish distinct Experience identity.",
    }

    thread_activity: dict[str, Counter[str]] = defaultdict(Counter)
    annotated_path_count = 0
    total_thread_paths = 0
    for row in rows:
        recall = row.get("recall", {}) if isinstance(row.get("recall"), dict) else {}
        evaluation = row.get("evaluation", {}) if isinstance(row.get("evaluation"), dict) else {}
        analysis = recall.get("activation_analysis", {}) if isinstance(recall.get("activation_analysis"), dict) else {}
        expected = {str(word) for word in _as_list(evaluation.get("expected_words"))}
        unexpected = {str(word) for word in _as_list(evaluation.get("unexpected_words"))}
        selected = {str(word) for word in _as_list(recall.get("selected_words"))}
        events = [event for event in _as_list(recall.get("stage_diagnostics")) if isinstance(event, dict)]
        for path in [item for item in _as_list(analysis.get("paths")) if isinstance(item, dict)]:
            source_thread = str(path.get("from_id")) if path.get("from_type") == "thread" else None
            if not source_thread or source_thread not in snapshot["threads"]:
                continue
            target_word = str(path.get("to_id")) if path.get("to_type") == "word" else ""
            total_thread_paths += 1
            activity = thread_activity[source_thread]
            activity["generated_paths"] += 1
            activity["activation_contribution"] += 1
            gate_events = [event for event in events if event.get("stage") == "ACTIVATION_GATE" and str(event.get("identifier")) == target_word]
            activity["gate_selection"] += int(any(bool(event.get("accepted")) for event in gate_events))
            activity["wm_admission"] += int(target_word in selected)
            if target_word in expected:
                activity["expected_contribution"] += 1
                annotated_path_count += 1
            elif target_word in unexpected:
                activity["unexpected_contribution"] += 1
                annotated_path_count += 1
            else:
                activity["unknown_contribution"] += 1

    instance_utility = []
    dominant_instances = []
    multiple_expected_evidence = 0
    for matrix_row in split_matrix:
        members = level_zero_groups[matrix_row["level_0_identity"]]
        utilities = [{"thread_id": thread_id, **dict(thread_activity[thread_id])} for thread_id in members]
        instance_utility.append({
            "level_0_identity": matrix_row["level_0_identity"],
            "member_words": matrix_row["member_words"],
            "instances": utilities,
        })
        if sum(item.get("expected_contribution", 0) > 0 for item in utilities) > 1:
            multiple_expected_evidence += 1
        path_total = sum(item.get("generated_paths", 0) for item in utilities)
        activation_total = sum(item.get("activation_contribution", 0) for item in utilities)
        wm_total = sum(item.get("wm_admission", 0) for item in utilities)
        dominant_instances.append({
            "level_0_identity": matrix_row["level_0_identity"],
            "instance_count": len(members),
            "top_instance_path_share": max((item.get("generated_paths", 0) for item in utilities), default=0) / path_total if path_total else None,
            "top_instance_activation_share": max((item.get("activation_contribution", 0) for item in utilities), default=0) / activation_total if activation_total else None,
            "top_instance_wm_share": max((item.get("wm_admission", 0) for item in utilities), default=0) / wm_total if wm_total else None,
        })

    recall_utility = {
        "annotation_coverage": annotated_path_count / total_thread_paths if total_thread_paths else 0.0,
        "level_0_groups_with_multiple_expected_instances": multiple_expected_evidence,
        "interpretation": "UNKNOWN" if not annotated_path_count else "ANNOTATED_SUBSET_ONLY",
        "target_used_for_identity": False,
    }

    roles = {
        "canonical_word_set": {"role": "IDENTITY_CANDIDATE", "basis": "canonical structural content"},
        "canonical_key": {"role": "IDENTITY_CANDIDATE", "basis": "derived from normalized word keys"},
        "source_text": {"role": "IDENTITY_CANDIDATE", "basis": "stored source utterance"},
        "created_by": {"role": "IDENTITY_CANDIDATE", "basis": "utterance producer, not semantic subject"},
        "date": {"role": "UNKNOWN_ROLE", "basis": "derived from storage time, not documented event time"},
        "created_at": {"role": "UNKNOWN_ROLE", "basis": "storage timestamp"},
        "last_seen": {"role": "MUTABLE_STATE_CANDIDATE", "basis": "updated observation timestamp"},
        "seen_count": {"role": "MUTABLE_STATE_CANDIDATE", "basis": "updated observation count"},
        "strength": {"role": "MUTABLE_STATE_CANDIDATE", "basis": "reinforcement strength"},
        "weight_in_thread": {"role": "UNKNOWN_ROLE", "basis": "stored connection weight; identity role unspecified"},
    }

    model_groups = {
        "MODEL_A_INSTANCE_IDENTITY": {thread_id: [thread_id] for thread_id in thread_ids},
        "MODEL_B_STRUCTURAL_IDENTITY": level_groups["LEVEL_0_WORD_SET"],
        "MODEL_C_CONTENT_ORIGIN_IDENTITY": level_groups["LEVEL_2_ORIGIN"],
        "MODEL_D_STRUCTURAL_WITH_MUTABLE_STATE": level_groups["LEVEL_0_WORD_SET"],
    }
    counterfactuals = {
        model: _model_topology(snapshot, groups, thread_activity, model)
        for model, groups in model_groups.items()
    }
    counterfactuals["MODEL_E_UNRESOLVED"] = {
        "model": "MODEL_E_UNRESOLVED",
        "marker": "OFFLINE_IDENTITY_COUNTERFACTUAL",
        "production_replay": False,
        "recall_quality_assumption": "NONE",
        "estimated_thread_identities": None,
        "estimated_repeat_state_updates": None,
        "estimated_connections": None,
        "estimated_connection_traversal_opportunities": None,
        "estimated_repeated_path_opportunities": None,
        "mean_fanout": None,
    }

    source_variation_exists = bool(source_variations)
    origin_variation_exists = state_difference_causes["created_by"] > 0
    risk_names = (
        "LOSS_OF_TEMPORAL_DISTINCTION", "LOSS_OF_SOURCE_TEXT_VARIATION", "LOSS_OF_ORIGIN",
        "LOSS_OF_REPETITION_STRENGTH", "OVER_SEPARATION", "STATE_COLLAPSE",
        "UNKNOWN_RECALL_IMPACT",
    )
    risk_true = {
        "MODEL_A_INSTANCE_IDENTITY": {"OVER_SEPARATION", "UNKNOWN_RECALL_IMPACT"},
        "MODEL_B_STRUCTURAL_IDENTITY": {
            *({"LOSS_OF_SOURCE_TEXT_VARIATION"} if source_variation_exists else set()),
            *({"LOSS_OF_ORIGIN"} if origin_variation_exists else set()),
            "LOSS_OF_TEMPORAL_DISTINCTION", "LOSS_OF_REPETITION_STRENGTH",
            "STATE_COLLAPSE", "UNKNOWN_RECALL_IMPACT",
        },
        "MODEL_C_CONTENT_ORIGIN_IDENTITY": {
            "LOSS_OF_TEMPORAL_DISTINCTION", "LOSS_OF_REPETITION_STRENGTH",
            "STATE_COLLAPSE", "UNKNOWN_RECALL_IMPACT",
        },
        "MODEL_D_STRUCTURAL_WITH_MUTABLE_STATE": {
            *({"LOSS_OF_SOURCE_TEXT_VARIATION"} if source_variation_exists else set()),
            *({"LOSS_OF_ORIGIN"} if origin_variation_exists else set()),
            "LOSS_OF_TEMPORAL_DISTINCTION", "UNKNOWN_RECALL_IMPACT",
        },
    }
    safety_risks = {
        model: {risk: risk in true_risks for risk in risk_names}
        for model, true_risks in risk_true.items()
    }
    safety_risks["MODEL_E_UNRESOLVED"] = {risk: "UNKNOWN" for risk in risk_names}

    reinforcement_review = {
        "frequency": "words.seen_count records repeated word observation",
        "thread_seen_count": "weighted mode may update an existing canonical-key thread; count mode creates instances",
        "strength": "mutable reinforcement state",
        "thread_repetition": "count mode preserves repeated conversations as countable traces",
        "connection_multiplicity": "each thread instance owns word_thread links",
        "classification": "POTENTIAL_REDUNDANT_REPETITION_REPRESENTATION",
        "bug_classification": False,
    }

    return {
        "thread_count": total,
        "identity_levels": identity_levels,
        "identity_split_matrix": split_matrix,
        "state_difference_causes": dict(state_difference_causes),
        "field_roles": roles,
        "same_experience_classification": dict(experience_classification),
        "source_text_variations": source_variations[:20],
        "temporal_identity_review": temporal_review,
        "recall_utility": recall_utility,
        "instance_utility": instance_utility,
        "instance_utility_attribution": "THREAD_PATH_SOURCE; Gate/WM values are observable target-path outcomes, not inferred semantic ownership",
        "dominant_instance_analysis": dominant_instances,
        "state_bearing_duplicates": dict(state_bearing),
        "reinforcement_representation_review": reinforcement_review,
        "connection_set_equivalence": dict(connection_equivalence),
        "candidate_models": {
            "MODEL_A_INSTANCE_IDENTITY": "Every stored Thread remains an identity",
            "MODEL_B_STRUCTURAL_IDENTITY": "Canonical word set identifies an Experience",
            "MODEL_C_CONTENT_ORIGIN_IDENTITY": "Word set, source text, and origin identify an Experience",
            "MODEL_D_STRUCTURAL_WITH_MUTABLE_STATE": "Structural identity plus separately represented repeat state hypothesis",
            "MODEL_E_UNRESOLVED": "Existing metadata cannot establish Experience identity",
        },
        "offline_identity_counterfactuals": counterfactuals,
        "identity_safety_risks": safety_risks,
        "integrity": {
            "same_word_set_is_same_experience": False,
            "same_experience_is_same_state": False,
            "repeated_experience_implies_multiple_experiences": False,
            "target_or_expected_label_used_for_identity": False,
            "production_mutation": False,
        },
    }


def compare_storage_identity(short: Mapping[str, Any], long: Mapping[str, Any]) -> dict[str, Any]:
    comparison = {}
    for level in LEVEL_FIELDS:
        before = short["identity_levels"][level]
        after = long["identity_levels"][level]
        comparison[level] = {
            "100_turn": before,
            "1000_turn": after,
            "unique_identity_delta": after["unique_identity_count"] - before["unique_identity_count"],
            "repeat_instance_delta": after["repeat_instance_count"] - before["repeat_instance_count"],
        }
    long_levels = long["identity_levels"]
    temporal_artifact = long["temporal_identity_review"]["timestamp_uniqueness_artifact"]
    source_splits = long_levels["LEVEL_1_SOURCE_TEXT"]["unique_identity_count"] > long_levels["LEVEL_0_WORD_SET"]["unique_identity_count"]
    state_differences = sum(long["state_difference_causes"].values()) > 0
    strength_state_gain = (long_levels["LEVEL_4_STRENGTH_STATE"]["identity_information_gain"] or 0.0) > 0
    if temporal_artifact and not source_splits and not strength_state_gain:
        classification = "IDENTITY_METADATA_INSUFFICIENT"
    elif temporal_artifact and (source_splits or strength_state_gain):
        classification = "MIXED_IDENTITY_PROBLEM"
    elif source_splits:
        classification = "IDENTITY_TOO_COARSE"
    elif strength_state_gain or state_differences:
        classification = "IDENTITY_AND_STATE_CONFLATED"
    elif long_levels["LEVEL_0_WORD_SET"]["over_separating"]:
        classification = "IDENTITY_TOO_FINE"
    elif not long["identity_split_matrix"]:
        classification = "IDENTITY_ALREADY_SUFFICIENT"
    else:
        classification = "IDENTITY_METADATA_INSUFFICIENT"
    direction = "ADD_MISSING_IDENTITY_METADATA" if classification in {"MIXED_IDENTITY_PROBLEM", "IDENTITY_METADATA_INSUFFICIENT"} else "REFINE_THREAD_IDENTITY" if classification == "IDENTITY_TOO_COARSE" else "SEPARATE_IDENTITY_AND_STATE" if classification == "IDENTITY_AND_STATE_CONFLATED" else "KEEP_INSTANCE_STORAGE" if classification == "IDENTITY_ALREADY_SUFFICIENT" else "MORE_EVIDENCE_REQUIRED"
    next_step = "missing metadata研究" if direction == "ADD_MISSING_IDENTITY_METADATA" else "identity/state separationのoffline prototype" if direction == "SEPARATE_IDENTITY_AND_STATE" else "reinforcement representation研究" if classification == "IDENTITY_TOO_FINE" else "現状storageを維持" if direction == "KEEP_INSTANCE_STORAGE" else "3000-turn baselineへ進む"
    return {
        "identity_level_comparison": comparison,
        "identity_classification": classification,
        "recommended_storage_direction": direction,
        "next_research_step": next_step,
        "production_migration": False,
    }


def select_storage_identity_review_queue(analysis: Mapping[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    return [{
        "review_type": "STORAGE_IDENTITY_SPLIT",
        "annotation_status": "REVIEW_REQUIRED",
        **row,
    } for row in analysis["identity_split_matrix"][:limit]]


def storage_identity_markdown(short: Mapping[str, Any], long: Mapping[str, Any], comparison: Mapping[str, Any]) -> str:
    lines = ["# Experience Thread Storage Identity Analysis", "", "## Summary", "", "Offline identity diagnostics only; no identity model is implemented."]
    sections = (
        ("Identity Levels", "identity_levels"),
        ("Identity Collapse", "identity_split_matrix"),
        ("State Difference Causes", "state_difference_causes"),
        ("Immutable Identity vs Mutable State", "field_roles"),
        ("Temporal Identity Review", "temporal_identity_review"),
        ("Recall Utility", "recall_utility"),
        ("Instance Utility", "dominant_instance_analysis"),
        ("Connection Equivalence", "connection_set_equivalence"),
        ("Candidate Identity Models", "candidate_models"),
        ("Offline Storage Counterfactual", "offline_identity_counterfactuals"),
        ("High-Fanout Impact", "offline_identity_counterfactuals"),
        ("Path Pressure Impact", "offline_identity_counterfactuals"),
        ("Safety Risks", "identity_safety_risks"),
    )
    for title, key in sections:
        lines.extend(["", f"## {title}", "", f"100: `{json.dumps(short[key], ensure_ascii=False, sort_keys=True)}`", "", f"1000: `{json.dumps(long[key], ensure_ascii=False, sort_keys=True)}`"])
    lines.extend([
        "", "## Integrity Review", "",
        "Same word set ≠ same Experience; same Experience ≠ same state; repeating an Experience ≠ proof that multiple Experiences exist.",
        "", "## Identity Classification", "", f"**{comparison['identity_classification']}**",
        "", "## Recommended Storage Direction", "", f"**{comparison['recommended_storage_direction']}**",
        "", "## Next Research Step", "", f"**{comparison['next_research_step']}**",
        "", "No Production migration, deduplication, upsert, merge, schema, learning, Recall, or reinforcement change was made.", "",
    ])
    return "\n".join(lines)
