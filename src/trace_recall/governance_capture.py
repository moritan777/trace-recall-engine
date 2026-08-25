"""Offline capture and evaluation of recall-governance observations.

This module deliberately consumes logger output rather than participating in the
runtime recall path.  Captures keep measurements and human judgements separate.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping

from .governance import RecallExpectation, parse_expectation


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: object required")
            rows.append(value)
    return rows


def load_annotations(path: Path | None) -> dict[int, dict[str, Any]]:
    annotations: dict[int, dict[str, Any]] = {}
    if path is None:
        return annotations
    for row in read_jsonl(path):
        turn = int(row["turn"])
        if turn in annotations:
            raise ValueError(f"duplicate annotation for turn {turn}")
        annotation = {k: v for k, v in row.items() if k != "turn"}
        if "expectation" in annotation:
            annotation["expectation"] = parse_expectation(annotation["expectation"]).value
        annotations[turn] = annotation
    return annotations


def capture_record(record: Mapping[str, Any], annotation: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Project a schema-v2 record without inventing unavailable observations."""
    if record.get("schema_version") != 2:
        raise ValueError("Research Logger schema_version 2 required")
    recall = record.get("recall") if isinstance(record.get("recall"), dict) else {}
    memory = record.get("working_memory") if isinstance(record.get("working_memory"), dict) else {}
    prompt = record.get("prompt") if isinstance(record.get("prompt"), dict) else {}
    evaluation = record.get("evaluation") if isinstance(record.get("evaluation"), dict) else {}
    response = record.get("response") if isinstance(record.get("response"), dict) else {}
    config = record.get("governance_observation_config") if isinstance(record.get("governance_observation_config"), dict) else {}
    diagnostics = _list(recall.get("stage_diagnostics"))
    selected_groups = _list(recall.get("selected_thread_groups"))
    selected_ids = [g.get("representative_thread_id", g.get("canonical_key")) for g in selected_groups if isinstance(g, dict)]
    selected_ids = [v for v in selected_ids if v is not None]
    observed = {
        "sequence": record.get("turn"),
        "input_text": record.get("input_text", ""),
        "mode": record.get("mode", ""),
        "diagnostic_stage_events": diagnostics,
        "recall_outcome": recall.get("outcome", ""),
        "topic_reentry_words": _list(recall.get("topic_reentry_words")),
        "candidate_ids": _list(recall.get("activated_threads")),
        "selected_ids": selected_ids,
        "selected_words": _list(recall.get("selected_words")),
        "working_memory_ids": [g.get("representative_thread_id", g.get("canonical_key")) for g in _list(memory.get("selected_thread_groups")) if isinstance(g, dict)],
        "working_memory_word_count": memory.get("word_count", 0),
        "working_memory_group_count": memory.get("thread_group_count", 0),
        "suppression_reasons": [
            {"identifier": e.get("identifier"), "stage": e.get("stage"), "reason": e.get("reason")}
            for e in diagnostics if isinstance(e, dict) and not e.get("accepted", True)
        ],
        "activation_scores": [
            {"identifier": e.get("identifier"), "input_score": e.get("input_score"), "output_score": e.get("output_score")}
            for e in diagnostics if isinstance(e, dict) and (e.get("input_score") is not None or e.get("output_score") is not None)
        ],
        "frequency_observations": [
            {"identifier": e.get("identifier"), "raw_frequency": e.get("raw_frequency"), "reinforcement_contribution": e.get("reinforcement_contribution")}
            for e in diagnostics if isinstance(e, dict) and (e.get("raw_frequency") or e.get("reinforcement_contribution"))
        ],
        "connection_paths": [
            {k: e.get(k) for k in ("source_trace", "connection", "destination")}
            for e in diagnostics if isinstance(e, dict) and any(e.get(k) for k in ("source_trace", "connection", "destination"))
        ],
        "prompt_chars": prompt.get("chars", len(prompt.get("text", "")) if isinstance(prompt.get("text"), str) else 0),
        "prompt_rough_tokens": prompt.get("rough_tokens", 0),
        "response_text": response.get("final_text", response.get("text", "")),
        "response_observed": bool(response.get("enabled", False)) and not bool(response.get("skipped", False)),
        "expected_hit_count": evaluation.get("expected_hit_count", 0),
        "unexpected_hit_count": evaluation.get("unexpected_hit_count", 0),
        "precision_like": evaluation.get("precision_like", 0.0),
        "runtime_config": dict(config),
    }
    result: dict[str, Any] = {"schema_version": 1, "fixture_type": "captured_governance_observation", "turn": record.get("turn"), "observed": observed}
    if annotation:
        result["annotation"] = dict(annotation)
    return result


def convert_research_records(records: Iterable[Mapping[str, Any]], annotations: Mapping[int, Mapping[str, Any]] | None = None) -> list[dict[str, Any]]:
    annotations = annotations or {}
    return [capture_record(row, annotations.get(int(row.get("turn") or 0))) for row in records]


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _normalise(row: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any] | None]:
    if row.get("fixture_type") == "captured_governance_observation":
        return row.get("observed", {}), row.get("annotation") if isinstance(row.get("annotation"), dict) else None
    # Artificial fixtures use the same evaluator through this adapter.
    return row.get("observed", row), row.get("annotation", row) if row.get("expectation") else row.get("annotation")


def evaluate_governance(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    observations = list(rows)
    annotated = 0
    denominators = Counter()
    annotation_counts = Counter()
    hits = Counter()
    candidate_observations = Counter()
    candidate_suppressions = Counter()
    root_cause_failures = Counter()
    must_not_speak_observations: list[dict[str, Any]] = []
    frequencies: list[float] = []
    connections = 0
    precision: list[float] = []
    unexpected = recalls = abstentions = reentries = fatigue = 0
    prompt_sizes: list[float] = []
    memory_sizes: list[float] = []
    fatigue_turns: list[int] = []
    fatigue_memory_sizes: list[float] = []
    non_fatigue_memory_sizes: list[float] = []
    explicit_reentry_recoveries = pseudo_reentry_false_positives = 0
    for row in observations:
        obs, ann = _normalise(row)
        selected = bool(_list(obs.get("selected_words")) or _list(obs.get("selected_ids")))
        recalls += int(selected)
        abstentions += int(not selected)
        reentries += int(bool(_list(obs.get("topic_reentry_words"))))
        turn_fatigue = sum(
            1 for event in _list(obs.get("diagnostic_stage_events"))
            if isinstance(event, dict) and not event.get("accepted", True)
            and ("fatigue" in str(event.get("reason", "")).lower() or float(event.get("fatigue_contribution", 0) or 0) != 0)
        )
        fatigue += turn_fatigue
        if turn_fatigue:
            fatigue_turns.append(int(row.get("turn", obs.get("sequence", 0)) or 0))
            fatigue_memory_sizes.append(float(obs.get("working_memory_word_count", 0) or 0))
        else:
            non_fatigue_memory_sizes.append(float(obs.get("working_memory_word_count", 0) or 0))
        unexpected += int(obs.get("unexpected_hit_count", 0) or 0)
        precision.append(float(obs.get("precision_like", 0.0) or 0.0))
        prompt_sizes.append(float(obs.get("prompt_rough_tokens", 0) or 0))
        memory_sizes.append(float(obs.get("working_memory_word_count", 0) or 0))
        connections += len(_list(obs.get("connection_paths")))
        for f in _list(obs.get("frequency_observations")):
            if isinstance(f, dict) and f.get("raw_frequency") is not None:
                frequencies.append(float(f["raw_frequency"]))
        events = [event for event in _list(obs.get("diagnostic_stage_events")) if isinstance(event, dict)]
        first_drop: dict[str, str] = {}
        for event in events:
            stage = str(event.get("stage", "UNKNOWN"))
            candidate_observations[stage] += 1
            identifier = str(event.get("identifier", ""))
            if not event.get("accepted", True) and identifier not in first_drop:
                # The recorder follows a rejected candidate through later stages.
                # Attribute its suppression once, at the first rejecting stage.
                first_drop[identifier] = stage
                candidate_suppressions[stage] += 1
        if not ann or not ann.get("expectation"):
            continue
        annotated += 1
        label = parse_expectation(ann["expectation"])
        annotation_counts[label.value] += 1
        response_observed = bool(obs.get("response_observed", "response_text" in obs))
        words = set(_list(ann.get("words")) or _list(ann.get("expected_words")))
        selected_words = set(_list(obs.get("selected_words")))
        coverage = set(str(item) for item in _list(ann.get("coverage")))
        if "explicit_topic_reentry" in coverage and bool(selected_words & words):
            explicit_reentry_recoveries += 1
        if "pseudo_reentry" in coverage and bool(selected_words & words):
            pseudo_reentry_false_positives += 1
        if label is RecallExpectation.MUST_NOT_SPEAK:
            response_text = str(obs.get("response_text", ""))
            must_not_speak_observations.append({
                "turn": row.get("turn", obs.get("sequence")), "targets": sorted(words),
                "recalled": bool(selected_words & words),
                "entered_working_memory": bool(selected_words & words),
                "generated_response": response_observed,
                "target_mentioned_in_response": response_observed and any(word in response_text for word in words),
            })
        if label is RecallExpectation.MUST_NOT_SPEAK and not response_observed:
            # A --no-response run cannot demonstrate either speech or silence.
            # Keep annotation coverage, but do not manufacture a leakage result.
            continue
        denominators[label.value] += 1
        any_matched = bool(selected_words & words) if words else selected
        all_matched = words <= selected_words if words else selected
        if label is RecallExpectation.SHOULD_RECALL:
            hits[label.value] += int(all_matched)
            missing = words - selected_words if words else (set() if selected else {"<turn>"})
            if missing:
                causes: list[str] = []
                by_identifier = {str(event.get("identifier", "")): event for event in events}
                for word in missing:
                    causes.append(first_drop.get(word, "RAW_ACTIVATION" if word not in by_identifier else str(by_identifier[word].get("stage", "UNKNOWN"))))
                # A turn is one failure. Pick the earliest root stage across its
                # missing targets rather than counting downstream propagation.
                order = ["EXTRACTION", "RAW_ACTIVATION", "ACTIVATION_GATE", "EXTERNAL_ADMISSION", "RECALL_SELECTION", "WORKING_MEMORY", "REVEAL_POLICY", "UNKNOWN"]
                root = min(causes, key=lambda stage: order.index(stage) if stage in order else len(order))
                root_cause_failures[root] += 1
        elif label is RecallExpectation.SHOULD_NOT_RECALL:
            hits[label.value] += int(any_matched)
        elif label is RecallExpectation.MUST_NOT_SPEAK:
            spoken = bool(obs.get("response_text"))
            hits[label.value] += int(spoken and (not words or any(w in str(obs.get("response_text")) for w in words)))
    def rate(key: str) -> float | None:
        return hits[key] / denominators[key] if denominators[key] else None
    return {
        "observation_count": len(observations), "annotation_count": annotated,
        "recall_precision": mean(precision) if precision else 0.0,
        "unexpected_recall": unexpected, "abstention_rate": abstentions / len(observations) if observations else 0.0,
        "topic_fatigue_suppressions": fatigue, "topic_reentry_turns": reentries,
        "first_fatigue_turn": min(fatigue_turns) if fatigue_turns else None,
        "explicit_reentry_recovery_count": explicit_reentry_recoveries,
        "pseudo_reentry_false_positive_count": pseudo_reentry_false_positives,
        "fatigue_working_memory_impact": {
            "fatigue_turn_average_words": mean(fatigue_memory_sizes) if fatigue_memory_sizes else None,
            "other_turn_average_words": mean(non_fatigue_memory_sizes) if non_fatigue_memory_sizes else None,
        },
        "average_prompt_tokens": mean(prompt_sizes) if prompt_sizes else 0.0,
        "average_working_memory_words": mean(memory_sizes) if memory_sizes else 0.0,
        "candidate_observations_by_stage": dict(sorted(candidate_observations.items())),
        "candidate_suppressions_by_stage": dict(sorted(candidate_suppressions.items())),
        "turn_level_root_cause_failures": dict(sorted(root_cause_failures.items())),
        "frequency_distribution": {"count": len(frequencies), "mean": mean(frequencies) if frequencies else 0.0, "max": max(frequencies, default=0.0)},
        "connection_path_usage": connections,
        "expectation_denominators": dict(denominators),
        "annotation_counts": dict(annotation_counts),
        "must_not_speak_observations": must_not_speak_observations,
        "should_recall_hit_rate": rate("SHOULD_RECALL"),
        "should_not_recall_leakage": rate("SHOULD_NOT_RECALL"),
        "must_not_speak_leakage": rate("MUST_NOT_SPEAK"),
    }


def comparison_markdown(named_results: Mapping[str, Mapping[str, Any]]) -> str:
    metrics = ["should_recall_hit_rate", "should_not_recall_leakage", "must_not_speak_leakage", "abstention_rate", "unexpected_recall", "topic_fatigue_suppressions", "topic_reentry_turns", "frequency_distribution", "turn_level_root_cause_failures", "average_prompt_tokens", "average_working_memory_words", "candidate_observations_by_stage", "candidate_suppressions_by_stage", "recall_precision", "connection_path_usage"]
    names = list(named_results)
    lines = ["# Governance Evaluation Comparison", "", "| Metric | " + " | ".join(names) + " |", "|---|" + "---:|" * len(names)]
    for metric in metrics:
        values = ["N/A" if named_results[n].get(metric) is None else json.dumps(named_results[n].get(metric), ensure_ascii=False, sort_keys=True) for n in names]
        lines.append(f"| {metric.replace('_', ' ').title()} | " + " | ".join(values) + " |")
    lines.extend(["", "Unannotated observations are excluded from all expectation denominators.", ""])
    return "\n".join(lines)


def build_failure_audits(rows: Iterable[Mapping[str, Any]], default_gate_threshold: float = 0.05) -> list[dict[str, Any]]:
    """Explain every annotated SHOULD_RECALL miss from captured diagnostics."""
    audits: list[dict[str, Any]] = []
    for row in rows:
        obs, ann = _normalise(row)
        if not ann or parse_expectation(ann.get("expectation", "MAY_RECALL")) is not RecallExpectation.SHOULD_RECALL:
            continue
        expected = [str(word) for word in _list(ann.get("words"))]
        selected = set(str(word) for word in _list(obs.get("selected_words")))
        missing = [word for word in expected if word not in selected]
        if not missing:
            continue
        events = [event for event in _list(obs.get("diagnostic_stage_events")) if isinstance(event, dict)]
        extracted = [str(event.get("identifier")) for event in events if event.get("stage") == "EXTRACTION" and event.get("accepted", True)]
        raw_events = [event for event in events if event.get("stage") == "RAW_ACTIVATION"]
        raw_by_word = {str(event.get("identifier")): event for event in raw_events}
        threshold = float((obs.get("runtime_config") or {}).get("gate_min_word_score", default_gate_threshold))
        targets: list[dict[str, Any]] = []
        roots: list[str] = []
        for word in missing:
            raw = raw_by_word.get(word)
            stages = {str(event.get("stage")): event for event in events if str(event.get("identifier")) == word}
            gate = stages.get("ACTIVATION_GATE")
            if raw is None:
                root = "RAW_ACTIVATION"
                classification = "missing connection"
            elif gate is not None and not gate.get("accepted", True):
                root = "ACTIVATION_GATE"
                classification = "gate suppression"
            else:
                root = "other"
                classification = "other"
            roots.append(root)
            score = raw.get("output_score", raw.get("input_score")) if raw else None
            targets.append({
                "word": word,
                "raw_activation_present": raw is not None,
                "activation_sources": str(raw.get("activation_source", "")).split(",") if raw else [],
                "activation_score": score,
                "frequency": raw.get("raw_frequency") if raw else None,
                "reinforcement_contribution": raw.get("reinforcement_contribution") if raw else None,
                "connection_path": {key: raw.get(key) for key in ("source_trace", "connection", "destination")} if raw else None,
                "activation_gate": _stage_audit(gate),
                "gate_threshold": threshold if gate is not None else None,
                "score_minus_gate_threshold": float(score) - threshold if gate is not None and score is not None else None,
                "recall_selection": _stage_audit(stages.get("RECALL_SELECTION")),
                "working_memory": _stage_audit(stages.get("WORKING_MEMORY")),
                "root_cause_stage": root,
                "classification": classification,
            })
        root = "RAW_ACTIVATION" if "RAW_ACTIVATION" in roots else roots[0]
        audits.append({
            "turn": row.get("turn", obs.get("sequence")), "input": obs.get("input_text", ""),
            "expected_words": expected, "missing_expected_words": missing, "extracted_words": extracted,
            "raw_activation_candidates": [
                {key: event.get(key) for key in ("identifier", "activation_source", "input_score", "output_score", "raw_frequency", "reinforcement_contribution", "source_trace", "connection", "destination")}
                for event in raw_events
            ],
            "targets": targets, "root_cause_stage": root,
        })
    return audits


def _stage_audit(event: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if event is None:
        return None
    return {"accepted": bool(event.get("accepted", False)), "reason": event.get("reason", ""), "input_score": event.get("input_score"), "output_score": event.get("output_score")}


def failure_audit_markdown(audits: Iterable[Mapping[str, Any]]) -> str:
    audits = list(audits)
    lines = ["# SHOULD_RECALL Failure Audit", "", f"- Failed turns: {len(audits)}", ""]
    for audit in audits:
        lines.extend([f"## Turn {audit['turn']}", "", f"- Input: `{audit['input']}`", f"- Expected: `{', '.join(audit['expected_words'])}`", f"- Missing: `{', '.join(audit['missing_expected_words'])}`", f"- Extracted: `{', '.join(audit['extracted_words'])}`", f"- Root-cause stage: `{audit['root_cause_stage']}`", "", "| target | classification | activation score | frequency | reinforcement | gate | threshold margin | selection | working memory |", "|---|---|---:|---:|---:|---|---:|---|---|"])
        for target in audit["targets"]:
            gate = target["activation_gate"]
            selection = target["recall_selection"]
            memory = target["working_memory"]
            lines.append(f"| {target['word']} | {target['classification']} | {target['activation_score'] if target['activation_score'] is not None else 'N/A'} | {target['frequency'] if target['frequency'] is not None else 'N/A'} | {target['reinforcement_contribution'] if target['reinforcement_contribution'] is not None else 'N/A'} | {gate['reason'] if gate else 'not observed'} | {target['score_minus_gate_threshold'] if target['score_minus_gate_threshold'] is not None else 'N/A'} | {selection['accepted'] if selection else 'not observed'} | {memory['accepted'] if memory else 'not observed'} |")
        lines.append("")
    return "\n".join(lines)
