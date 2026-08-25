"""Offline audit of missing Experience identity provenance metadata.

The audit reads a conversation fixture, Research Logger records, and a final
SQLite snapshot.  It neither adds metadata nor changes Production storage.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping

from .repeated_experience import _load_snapshot


LOSS_CLASSES = (
    "NEVER_AVAILABLE", "AVAILABLE_UPSTREAM_LOST_BEFORE_STORAGE",
    "AVAILABLE_IN_LOG_ONLY", "ALREADY_PERSISTED", "UNKNOWN",
)


def _role(item: Mapping[str, Any]) -> str:
    return str(item.get("role", "user"))


def _text(item: Mapping[str, Any]) -> str:
    if item.get("text") is not None:
        return str(item["text"])
    role = _role(item)
    if role == "assistant" and item.get("assistant") is not None:
        return str(item["assistant"])
    return str(item.get("user", ""))


def _word_set_key(words: Iterable[str]) -> str:
    return json.dumps(sorted({str(word) for word in words}), ensure_ascii=False, separators=(",", ":"))


def _identity_metrics(keys: list[str]) -> dict[str, Any]:
    counts = Counter(keys)
    total = len(keys)
    repeats = total - len(counts)
    return {
        "unique_identities": len(counts),
        "repeat_instances": repeats,
        "repeat_ratio": repeats / total if total else 0.0,
        "max_repetition": max(counts.values(), default=0),
    }


def _metadata_inventory() -> list[dict[str, Any]]:
    return [
        {"field": "thread_id", "meaning": "stored Thread instance identifier", "created_when": "thread insert", "updated_when": "never", "mutability": "IMMUTABLE", "source": "random UUID fragment in create_thread", "precision_or_granularity": "one stored Thread instance", "nullable": False, "runtime_use": "thread lookup and traversal"},
        {"field": "date", "meaning": "UTC storage date", "created_when": "thread insert", "updated_when": "never", "mutability": "IMMUTABLE", "source": "now_iso()[0:10]", "precision_or_granularity": "day", "nullable": False, "runtime_use": "display/thread record"},
        {"field": "source_text", "meaning": "source utterance text", "created_when": "learn calls create_thread", "updated_when": "never", "mutability": "IMMUTABLE", "source": "conversation text", "precision_or_granularity": "full stored string", "nullable": True, "runtime_use": "storage/audit, not recall score"},
        {"field": "canonical_key", "meaning": "normalized sorted word combination key", "created_when": "before thread insert", "updated_when": "never", "mutability": "IMMUTABLE", "source": "extracted normalized words", "precision_or_granularity": "word-set structural key", "nullable": True, "runtime_use": "ThreadGroup/reuse lookup"},
        {"field": "strength", "meaning": "Thread reinforcement strength", "created_when": "thread insert", "updated_when": "weighted exact-key reuse", "mutability": "MUTABLE", "source": "default 1.0 or weighted reinforcement", "precision_or_granularity": "floating point capped at 4.0", "nullable": False, "runtime_use": "activation/thread scoring"},
        {"field": "created_at", "meaning": "UTC storage timestamp", "created_when": "thread insert", "updated_when": "never", "mutability": "IMMUTABLE", "source": "now_iso()", "precision_or_granularity": "seconds", "nullable": True, "runtime_use": "ordering/age metadata"},
        {"field": "last_seen", "meaning": "last Thread observation timestamp", "created_when": "thread insert", "updated_when": "weighted exact-key reuse", "mutability": "MUTABLE", "source": "now_iso()", "precision_or_granularity": "seconds", "nullable": True, "runtime_use": "stored Thread state"},
        {"field": "seen_count", "meaning": "Thread observation count", "created_when": "thread insert", "updated_when": "weighted exact-key reuse", "mutability": "MUTABLE", "source": "1 then increment", "precision_or_granularity": "integer count", "nullable": False, "runtime_use": "effective strength/reporting"},
        {"field": "created_by", "meaning": "utterance producer, not semantic subject", "created_when": "thread insert", "updated_when": "weighted reuse can replace value", "mutability": "CONDITIONALLY_MUTABLE", "source": "conversation role", "precision_or_granularity": "normalized user/assistant origin", "nullable": False, "runtime_use": "origin reporting/group metadata"},
        {"field": "weight_in_thread", "meaning": "word weight within one Thread", "created_when": "word_thread insert", "updated_when": "INSERT OR REPLACE for same link", "mutability": "CONDITIONALLY_MUTABLE", "source": "extractor word weight", "precision_or_granularity": "floating point", "nullable": False, "runtime_use": "activation propagation"},
        {"field": "added_at", "meaning": "word_thread storage timestamp", "created_when": "word_thread insert", "updated_when": "link replacement", "mutability": "CONDITIONALLY_MUTABLE", "source": "now_iso()", "precision_or_granularity": "seconds", "nullable": True, "runtime_use": "stored connection metadata"},
    ]


def _map_source_turns(conversation: list[Mapping[str, Any]], snapshot: Mapping[str, Any]) -> dict[str, Any]:
    learn_turns: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for sequence, item in enumerate(conversation, start=1):
        if item.get("mode") != "learn":
            continue
        learn_turns[(_text(item), _role(item))].append({
            "turn": int(item.get("turn", sequence)), "sequence": sequence,
            "text": _text(item), "role": _role(item),
            "message_id": item.get("message_id") or item.get("record_id") or item.get("id"),
            "session_id": item.get("session_id"),
        })
    stored: dict[tuple[str, str], list[str]] = defaultdict(list)
    for thread_id, row in snapshot["threads"].items():
        stored[(str(row.get("source_text", "")), str(row.get("created_by", "user")))].append(thread_id)
    for members in stored.values():
        members.sort(key=lambda thread_id: (str(snapshot["threads"][thread_id].get("created_at", "")), thread_id))
    for turns in learn_turns.values():
        turns.sort(key=lambda row: (row["turn"], row["sequence"]))

    thread_to_source: dict[str, dict[str, Any]] = {}
    source_to_threads: dict[int, list[str]] = defaultdict(list)
    unmatched_turns = []
    unmatched_threads = []
    group_mismatches = []
    for identity in sorted(set(learn_turns) | set(stored)):
        turns = learn_turns.get(identity, [])
        members = stored.get(identity, [])
        paired = min(len(turns), len(members))
        for index in range(paired):
            source = turns[index]
            thread_id = members[index]
            thread_to_source[thread_id] = source
            source_to_threads[source["turn"]].append(thread_id)
        unmatched_turns.extend(turns[paired:])
        unmatched_threads.extend(members[paired:])
        if len(turns) != len(members):
            group_mismatches.append({"source_text": identity[0], "created_by": identity[1], "learn_turn_count": len(turns), "stored_thread_count": len(members)})
    return {
        "thread_to_source": thread_to_source,
        "source_to_threads": dict(source_to_threads),
        "unmatched_turns": unmatched_turns,
        "unmatched_threads": unmatched_threads,
        "group_mismatches": group_mismatches,
        "learn_turn_count": sum(len(values) for values in learn_turns.values()),
        "mapped_thread_count": len(thread_to_source),
    }


def analyze_identity_metadata(
    conversation: Iterable[Mapping[str, Any]], research_records: Iterable[Mapping[str, Any]],
    db_path: Path,
) -> dict[str, Any]:
    """Audit provenance loss without mutating source records or the database."""
    turns = list(conversation)
    logs = list(research_records)
    snapshot = _load_snapshot(db_path)
    mapping = _map_source_turns(turns, snapshot)
    thread_to_source = mapping["thread_to_source"]

    provenance_chain = [
        {"stage": "CONVERSATION_RECORD", "available_identity": ["turn", "input sequence", "text", "role"], "missing_identity": ["event identity", "session identity", "message identity unless fixture supplies it"]},
        {"stage": "EXTRACTOR", "available_identity": ["text", "role", "extracted words"], "missing_identity": ["turn is not an extractor argument"]},
        {"stage": "LEARN_OPERATION", "available_identity": ["fixture turn in eval runner", "text", "role", "extracted words"], "missing_identity": ["event identity"]},
        {"stage": "THREAD_FACTORY", "available_identity": ["text", "role", "extracted words", "canonical key", "storage time"], "missing_identity": ["source turn", "message", "session", "event", "observation identity"]},
        {"stage": "DB_INSERT", "available_identity": ["thread_id", "source_text", "created_by", "canonical key", "storage timestamps", "mutable state"], "missing_identity": ["source turn", "message", "session", "event", "observation identity"]},
        {"stage": "RESEARCH_LOGGER", "available_identity": ["ask turn identifiers"], "missing_identity": ["learn/source turn mapping; learn turns are not schema-v2 research rows"]},
    ]

    fixture_has_message = any(item.get("message_id") or item.get("record_id") or item.get("id") for item in turns)
    fixture_has_session = any(item.get("session_id") for item in turns)
    information_loss_map = {
        "SOURCE_TURN_INDEX": {"classification": "AVAILABLE_UPSTREAM_LOST_BEFORE_STORAGE", "available_at": ["conversation fixture", "eval runner", "learn event result"], "unavailable_at": ["extractor API", "create_thread API", "threads table", "Research Logger learn rows"]},
        "INPUT_SEQUENCE": {"classification": "AVAILABLE_UPSTREAM_LOST_BEFORE_STORAGE", "available_at": ["conversation JSONL ordering", "eval runner"], "unavailable_at": ["threads table"]},
        "SOURCE_TEXT": {"classification": "ALREADY_PERSISTED", "available_at": ["fixture", "extractor caller", "threads.source_text"], "unavailable_at": []},
        "CREATED_BY": {"classification": "ALREADY_PERSISTED", "available_at": ["fixture role", "threads.created_by"], "unavailable_at": []},
        "EXTRACTED_WORD_SET": {"classification": "ALREADY_PERSISTED", "available_at": ["extractor", "word_threads topology", "canonical_key"], "unavailable_at": []},
        "SOURCE_MESSAGE_ID": {"classification": "AVAILABLE_UPSTREAM_LOST_BEFORE_STORAGE" if fixture_has_message else "NEVER_AVAILABLE", "available_at": ["conversation fixture"] if fixture_has_message else [], "unavailable_at": ["threads table"]},
        "SESSION_ID": {"classification": "AVAILABLE_UPSTREAM_LOST_BEFORE_STORAGE" if fixture_has_session else "NEVER_AVAILABLE", "available_at": ["conversation fixture"] if fixture_has_session else [], "unavailable_at": ["threads table"]},
        "SOURCE_EVENT_ID": {"classification": "NEVER_AVAILABLE", "available_at": [], "unavailable_at": ["fixture", "pipeline", "threads table"]},
        "OBSERVATION_ID": {"classification": "NEVER_AVAILABLE", "available_at": [], "unavailable_at": ["fixture", "pipeline", "threads table"]},
        "ASK_TURN_INDEX": {"classification": "AVAILABLE_IN_LOG_ONLY", "available_at": ["Research Logger ask records"], "unavailable_at": ["threads table", "learn/source mapping"]},
        "THREAD_ID": {"classification": "ALREADY_PERSISTED", "available_at": ["thread factory", "threads.thread_id", "learn event result"], "unavailable_at": ["source fixture"]},
    }

    source_turn_rows = []
    intra_turn = Counter()
    for item in turns:
        if item.get("mode") != "learn":
            continue
        turn = int(item.get("turn", len(source_turn_rows) + 1))
        member_ids = mapping["source_to_threads"].get(turn, [])
        signatures = [_word_set_key(snapshot["thread_words"][thread_id]) for thread_id in member_ids]
        duplicate_count = len(signatures) - len(set(signatures))
        source_turn_rows.append({
            "source_turn": turn, "source_text": _text(item),
            "created_thread_count": len(member_ids),
            "unique_thread_signatures": len(set(signatures)),
            "duplicate_thread_signatures_within_turn": duplicate_count,
            "thread_ids": member_ids,
        })
        intra_turn["source_turn_count"] += 1
        intra_turn["created_thread_count"] += len(member_ids)
        intra_turn["duplicate_signature_instances"] += duplicate_count
        intra_turn["turns_with_intra_turn_duplication"] += int(duplicate_count > 0)
    intra_turn["classification"] = "INTRA_TURN_DUPLICATION" if intra_turn["turns_with_intra_turn_duplication"] else "NO_INTRA_TURN_DUPLICATION_OBSERVED"

    signature_sources: dict[str, list[dict[str, Any]]] = defaultdict(list)
    signature_threads: dict[str, list[str]] = defaultdict(list)
    for thread_id in sorted(snapshot["threads"]):
        signature = _word_set_key(snapshot["thread_words"][thread_id])
        signature_threads[signature].append(thread_id)
        source = thread_to_source.get(thread_id)
        if source:
            signature_sources[signature].append(source)
    repeated_audit = []
    origin_counts = Counter()
    inter_turn = Counter()
    for signature, member_ids in signature_threads.items():
        if len(member_ids) <= 1:
            continue
        sources = signature_sources.get(signature, [])
        turns_for_signature = sorted({source["turn"] for source in sources})
        texts = sorted({source["text"] for source in sources})
        text_counts = Counter(source["text"] for source in sources)
        exact_input = any(count > 1 for count in text_counts.values()) and len(turns_for_signature) > 1
        different_input_same_words = len(texts) > 1
        same_source_distinct_turn = exact_input
        duplicated_source_turn = any(
            sum(_word_set_key(snapshot["thread_words"][thread_id]) == signature for thread_id in mapping["source_to_threads"].get(turn, [])) > 1
            for turn in turns_for_signature
        )
        if duplicated_source_turn:
            classification = "SAME_SOURCE_TURN_DUPLICATED_STORAGE"
        elif different_input_same_words:
            classification = "SEMANTICALLY_SIMILAR_INPUT"
        elif exact_input:
            classification = "EXACT_INPUT_REPETITION"
        else:
            classification = "UNKNOWN_ORIGIN"
        origin_counts[classification] += 1
        if same_source_distinct_turn:
            origin_counts["SAME_DESCRIPTION_DISTINCT_TURN"] += 1
        inter_turn["repeated_signature_groups"] += 1
        inter_turn["same_exact_input_groups"] += int(exact_input)
        inter_turn["same_source_text_groups"] += int(same_source_distinct_turn)
        inter_turn["same_extracted_words_groups"] += int(len(turns_for_signature) > 1)
        inter_turn["different_source_same_word_set_groups"] += int(different_input_same_words)
        repeated_audit.append({
            "signature": signature,
            "member_words": json.loads(signature),
            "repeat_thread_count": len(member_ids),
            "source_texts": texts,
            "source_conversation_turns": turns_for_signature,
            "same_exact_input_repeated": exact_input,
            "different_input_producing_same_signature": different_input_same_words,
            "same_description_distinct_turn": same_source_distinct_turn,
            "same_source_turn_duplicated_storage": duplicated_source_turn,
            "same_event_description_repeated": "UNRESOLVABLE",
            "different_conversation_event": "UNRESOLVABLE",
            "origin_classification": classification,
        })
    repeated_audit.sort(key=lambda row: (-row["repeat_thread_count"], row["signature"]))
    for label in ("EXACT_INPUT_REPETITION", "SEMANTICALLY_SIMILAR_INPUT", "SAME_DESCRIPTION_DISTINCT_TURN", "SAME_SOURCE_TURN_DUPLICATED_STORAGE", "UNKNOWN_ORIGIN"):
        origin_counts[label] += 0
    inter_turn["classification"] = "INTER_TURN_REPETITION" if inter_turn["repeated_signature_groups"] else "NO_INTER_TURN_REPETITION"

    mapped_threads = list(thread_to_source)
    word_set_keys = [_word_set_key(snapshot["thread_words"][thread_id]) for thread_id in sorted(snapshot["threads"])]
    source_turn_keys = [
        json.dumps([_word_set_key(snapshot["thread_words"][thread_id]), thread_to_source[thread_id]["turn"]], ensure_ascii=False)
        if thread_id in thread_to_source else json.dumps([_word_set_key(snapshot["thread_words"][thread_id]), "UNMAPPED", thread_id], ensure_ascii=False)
        for thread_id in sorted(snapshot["threads"])
    ]
    source_turn_counterfactual = {
        "marker": "OFFLINE_METADATA_COUNTERFACTUAL",
        "production_schema_change": False,
        "recall_quality_assumption": "NONE",
        "identity": "WORD_SET_PLUS_SOURCE_TURN_ID",
        **_identity_metrics(source_turn_keys),
        "mapping_coverage": len(mapped_threads) / len(snapshot["threads"]) if snapshot["threads"] else 0.0,
    }
    message_keys = []
    for thread_id in sorted(snapshot["threads"]):
        source = thread_to_source.get(thread_id)
        if not source or source.get("message_id") is None:
            message_keys = []
            break
        message_keys.append(json.dumps([_word_set_key(snapshot["thread_words"][thread_id]), source["message_id"]], ensure_ascii=False))
    message_counterfactual = ({"status": "AVAILABLE", "marker": "OFFLINE_METADATA_COUNTERFACTUAL", "production_schema_change": False, "recall_quality_assumption": "NONE", **_identity_metrics(message_keys)} if message_keys else {"status": "UNAVAILABLE", "reason": "fixture has no complete message identity"})
    session_keys = []
    if fixture_has_session:
        for thread_id in sorted(snapshot["threads"]):
            source = thread_to_source.get(thread_id)
            if not source or source.get("session_id") is None:
                session_keys = []
                break
            session_keys.append(json.dumps([_word_set_key(snapshot["thread_words"][thread_id]), source["session_id"], source["turn"]], ensure_ascii=False))
    session_counterfactual = ({"status": "AVAILABLE_FOR_AUDIT_ONLY", "marker": "OFFLINE_METADATA_COUNTERFACTUAL", "production_schema_change": False, "recall_quality_assumption": "NONE", **_identity_metrics(session_keys)} if session_keys else {"status": "UNAVAILABLE", "reason": "fixture/pipeline has no complete session identity"})

    timestamps = [str(row.get("created_at")) for row in snapshot["threads"].values() if row.get("created_at")]
    timestamp_counts = Counter(timestamps)
    timestamp_identity_keys = [json.dumps([_word_set_key(snapshot["thread_words"][thread_id]), snapshot["threads"][thread_id].get("created_at")], ensure_ascii=False) for thread_id in sorted(snapshot["threads"])]
    timestamp_identity_metrics = _identity_metrics(timestamp_identity_keys)
    structural_identity_metrics = _identity_metrics(word_set_keys)
    timestamp_added_identities = timestamp_identity_metrics["unique_identities"] - structural_identity_metrics["unique_identities"]
    timestamp_audit = {
        "date_classification": "STORAGE_TIME",
        "created_at_classification": "STORAGE_TIME",
        "last_seen_classification": "STORAGE_TIME_OR_MUTABLE_OBSERVATION_TIME",
        "precision": "seconds (now_iso timespec=seconds)",
        "timestamp_count": len(timestamps),
        "unique_timestamp_count": len(timestamp_counts),
        "unique_timestamp_ratio": len(timestamp_counts) / len(timestamps) if timestamps else 0.0,
        "same_timestamp_collision_count": len(timestamps) - len(timestamp_counts),
        "max_same_timestamp_count": max(timestamp_counts.values(), default=0),
        "timestamp_added_identity_count": timestamp_added_identities,
        "identity_artifact": "TIMESTAMP_IDENTITY_ARTIFACT" if timestamp_added_identities > 0 else "NOT_OBSERVED",
        "event_time_evidence": False,
    }

    mutable_state = {
        "threads.seen_count": {"classification": "MUTABLE_STATE", "updated_by": ["weighted exact-key reuse"], "identity": False},
        "threads.strength": {"classification": "MUTABLE_STATE", "updated_by": ["weighted exact-key reuse"], "identity": False},
        "threads.last_seen": {"classification": "MUTABLE_STATE", "updated_by": ["weighted exact-key reuse"], "identity": False},
        "words.seen_count (frequency)": {"classification": "MUTABLE_STATE", "updated_by": ["learn word upsert", "recall reinforce_seen"], "identity": False},
        "words.strength": {"classification": "MUTABLE_STATE", "updated_by": ["learn word upsert", "recall reinforce_seen"], "identity": False},
    }
    thread_policy = {
        "analyzed_mode": "count",
        "creation_trigger": "one create_thread call for each learn turn",
        "count_mode": "ALWAYS_INSERT_NEW_THREAD; no existing identity lookup",
        "weighted_mode": "EXACT_KEY_REUSE by canonical_key, updating strength/seen_count/last_seen",
        "new_word_combination_required": False,
        "new_source_text_required": False,
        "new_event_required": False,
        "reuse_classification_for_analyzed_baseline": "NO_REUSE",
        "duplicate_creation_boundary": "ThreadedConceptMemoryStore.create_thread persistence layer",
        "layer_audit": {
            "Extractor": "produces words; does not decide Thread identity",
            "Learn service/eval runner": "calls create_thread once per learn turn; does not pass source turn identity",
            "Thread factory/persistence": "count mode inserts; weighted mode alone performs canonical-key lookup",
            "Connection builder": "creates links after Thread identity decision; no reuse decision",
        },
    }

    missing_candidates = {
        "SOURCE_TURN_ID": {"evidence": "fixture/eval runner has turn but create_thread/DB do not", "what_it_identifies": "source observation occurrence", "immutable": True, "generated_where": "conversation source/eval runner", "persists_across_replay": "YES_IF_FIXTURE_TURN_STABLE", "distinguishes_occurrence": True, "distinguishes_description": False, "distinguishes_observation": True, "distinguishes_event": False},
        "SOURCE_EVENT_ID": {"evidence": "same description cannot be resolved as same versus distinct event", "what_it_identifies": "domain event occurrence", "immutable": True, "generated_where": "UNAVAILABLE; must originate upstream with event semantics", "persists_across_replay": "UNKNOWN", "distinguishes_occurrence": True, "distinguishes_description": False, "distinguishes_observation": False, "distinguishes_event": True},
    }

    total_connections = len(snapshot["links"])
    structural = _identity_metrics(word_set_keys)
    models = {
        "MODEL_A_CURRENT": {"estimated_identity_count": len(snapshot["threads"]), "estimated_repeated_observations": structural["repeat_instances"], "estimated_thread_records": len(snapshot["threads"]), "estimated_connections": total_connections, "status": "CURRENT_INSTANCE_STORAGE"},
        "MODEL_B_DESCRIPTION_PLUS_OCCURRENCE": {"estimated_identity_count": source_turn_counterfactual["unique_identities"], "estimated_repeated_observations": structural["repeat_instances"], "estimated_thread_records": source_turn_counterfactual["unique_identities"], "estimated_connections": total_connections, "status": "OFFLINE_ONLY"},
        "MODEL_C_DESCRIPTION_PLUS_SOURCE_TURN": {"estimated_identity_count": source_turn_counterfactual["unique_identities"], "estimated_repeated_observations": structural["repeat_instances"], "estimated_thread_records": source_turn_counterfactual["unique_identities"], "estimated_connections": total_connections, "status": "OFFLINE_ONLY"},
        "MODEL_D_EVENT_WITH_MUTABLE_REPETITION_STATE": {"estimated_identity_count": None, "estimated_repeated_observations": None, "estimated_thread_records": None, "estimated_connections": None, "status": "UNAVAILABLE_WITHOUT_SOURCE_EVENT_ID"},
        "MODEL_E_INSUFFICIENT_SOURCE_PROVENANCE": {"estimated_identity_count": None, "estimated_repeated_observations": None, "estimated_thread_records": None, "estimated_connections": None, "status": "OBSERVED_LIMIT"},
    }
    for model in models.values():
        model.update({"marker": "OFFLINE_METADATA_COUNTERFACTUAL", "production_schema_change": False, "recall_quality_assumption": "NONE"})

    root_cause = "MULTIPLE_IDENTITY_GAPS"
    direction = "SEPARATE_DESCRIPTION_AND_OCCURRENCE"
    next_step = "missing identity metadataのoffline prototype"
    return {
        "conversation_turn_count": len(turns),
        "research_log_record_count": len(logs),
        "thread_count": len(snapshot["threads"]),
        "current_metadata_inventory": _metadata_inventory(),
        "provenance_chain": provenance_chain,
        "information_loss_map": information_loss_map,
        "conceptual_separation": {
            "DESCRIPTION_IDENTITY": "what the memory describes",
            "OCCURRENCE_IDENTITY": "which event occurrence it is",
            "OBSERVATION_IDENTITY": "which source observation recorded it",
            "REPETITION_STATE": "how often/statefully it was observed",
            "equivalent": False,
        },
        "source_mapping": {
            "learn_turn_count": mapping["learn_turn_count"],
            "mapped_thread_count": mapping["mapped_thread_count"],
            "mapping_coverage": mapping["mapped_thread_count"] / len(snapshot["threads"]) if snapshot["threads"] else 0.0,
            "unmatched_turn_count": len(mapping["unmatched_turns"]),
            "unmatched_thread_count": len(mapping["unmatched_threads"]),
            "group_mismatches": mapping["group_mismatches"],
            "method": "deterministic source_text+created_by occurrence-order mapping",
            "pairing_certainty": "GROUP_COUNT_EXACT; INSTANCE_PAIRING_AMBIGUOUS_WHEN_TIMESTAMPS_COLLIDE",
        },
        "top_repeated_fixture_sources": repeated_audit[:20],
        "repetition_origin_classification": dict(origin_counts),
        "repetition_origin_counts_are_non_exclusive": True,
        "source_turn_thread_mapping": source_turn_rows,
        "intra_turn_duplication": dict(intra_turn),
        "inter_turn_repetition": dict(inter_turn),
        "source_turn_counterfactual": source_turn_counterfactual,
        "source_message_counterfactual": message_counterfactual,
        "session_identity": session_counterfactual,
        "temporal_metadata_audit": timestamp_audit,
        "mutable_state_audit": mutable_state,
        "thread_creation_policy": thread_policy,
        "missing_metadata_candidates": missing_candidates,
        "minimal_metadata_principle": "distinguish description, event occurrence, and observation with the fewest upstream-grounded fields; uniqueness alone is not the objective",
        "candidate_identity_models": models,
        "root_cause": root_cause,
        "recommended_metadata_direction": direction,
        "next_recommended_step": next_step,
        "integrity": {"production_schema_change": False, "production_mutation": False, "semantic_model_used": False},
    }


def select_identity_metadata_review_queue(analysis: Mapping[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    return [{"review_type": "REPEATED_FIXTURE_PROVENANCE", "annotation_status": "REVIEW_REQUIRED", **row} for row in analysis["top_repeated_fixture_sources"][:limit]]


def identity_metadata_markdown(analysis: Mapping[str, Any]) -> str:
    lines = ["# Missing Experience Identity Metadata Research", "", "## Summary", "", "Offline provenance and metadata-loss audit only; no schema or storage change is implemented."]
    sections = (
        ("Current Metadata Inventory", "current_metadata_inventory"),
        ("Provenance Chain", "provenance_chain"),
        ("Information Loss Map", "information_loss_map"),
        ("Thread Creation Policy", "thread_creation_policy"),
        ("Intra-turn Duplication", "intra_turn_duplication"),
        ("Inter-turn Repetition", "inter_turn_repetition"),
        ("Temporal Metadata", "temporal_metadata_audit"),
        ("Mutable State", "mutable_state_audit"),
        ("Missing Metadata Candidates", "missing_metadata_candidates"),
        ("Identity Model Comparison", "candidate_identity_models"),
        ("Offline Counterfactual", "source_turn_counterfactual"),
    )
    for title, key in sections:
        lines.extend(["", f"## {title}", "", f"`{json.dumps(analysis[key], ensure_ascii=False, sort_keys=True)}`"])
    lines.extend([
        "", "## Integrity Review", "",
        "Description Identity ≠ Occurrence Identity ≠ Observation Identity ≠ Mutable Repetition State.",
        "", "## Root Cause", "", f"**{analysis['root_cause']}**",
        "", "## Recommended Metadata Direction", "", f"**{analysis['recommended_metadata_direction']}**",
        "", "## Next Recommended Step", "", f"**{analysis['next_recommended_step']}**",
        "", "No metadata column, migration, deduplication, upsert, merge, connection rewrite, or Production behavior was changed.", "",
    ])
    return "\n".join(lines)
