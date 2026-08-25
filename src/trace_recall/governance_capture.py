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
        "expected_hit_count": evaluation.get("expected_hit_count", 0),
        "unexpected_hit_count": evaluation.get("unexpected_hit_count", 0),
        "precision_like": evaluation.get("precision_like", 0.0),
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
    hits = Counter()
    stage_failures = Counter()
    frequencies: list[float] = []
    connections = 0
    precision: list[float] = []
    unexpected = recalls = abstentions = reentries = fatigue = 0
    prompt_sizes: list[float] = []
    memory_sizes: list[float] = []
    for row in observations:
        obs, ann = _normalise(row)
        selected = bool(_list(obs.get("selected_words")) or _list(obs.get("selected_ids")))
        recalls += int(selected)
        abstentions += int(not selected)
        reentries += int(bool(_list(obs.get("topic_reentry_words"))))
        fatigue += sum(
            1 for event in _list(obs.get("diagnostic_stage_events"))
            if isinstance(event, dict) and not event.get("accepted", True)
            and ("fatigue" in str(event.get("reason", "")).lower() or float(event.get("fatigue_contribution", 0) or 0) > 0)
        )
        unexpected += int(obs.get("unexpected_hit_count", 0) or 0)
        precision.append(float(obs.get("precision_like", 0.0) or 0.0))
        prompt_sizes.append(float(obs.get("prompt_rough_tokens", 0) or 0))
        memory_sizes.append(float(obs.get("working_memory_word_count", 0) or 0))
        connections += len(_list(obs.get("connection_paths")))
        for f in _list(obs.get("frequency_observations")):
            if isinstance(f, dict) and f.get("raw_frequency") is not None:
                frequencies.append(float(f["raw_frequency"]))
        for event in _list(obs.get("diagnostic_stage_events")):
            if isinstance(event, dict) and not event.get("accepted", True):
                stage_failures[str(event.get("stage", "UNKNOWN"))] += 1
        if not ann or not ann.get("expectation"):
            continue
        annotated += 1
        label = parse_expectation(ann["expectation"])
        denominators[label.value] += 1
        words = set(_list(ann.get("words")) or _list(ann.get("expected_words")))
        selected_words = set(_list(obs.get("selected_words")))
        matched = bool(selected_words & words) if words else selected
        if label is RecallExpectation.SHOULD_RECALL:
            hits[label.value] += int(matched)
        elif label is RecallExpectation.SHOULD_NOT_RECALL:
            hits[label.value] += int(matched)
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
        "average_prompt_tokens": mean(prompt_sizes) if prompt_sizes else 0.0,
        "average_working_memory_words": mean(memory_sizes) if memory_sizes else 0.0,
        "stage_failure_distribution": dict(sorted(stage_failures.items())),
        "frequency_distribution": {"count": len(frequencies), "mean": mean(frequencies) if frequencies else 0.0, "max": max(frequencies, default=0.0)},
        "connection_path_usage": connections,
        "expectation_denominators": dict(denominators),
        "should_recall_hit_rate": rate("SHOULD_RECALL"),
        "should_not_recall_leakage": rate("SHOULD_NOT_RECALL"),
        "must_not_speak_leakage": rate("MUST_NOT_SPEAK"),
    }


def comparison_markdown(named_results: Mapping[str, Mapping[str, Any]]) -> str:
    metrics = ["recall_precision", "unexpected_recall", "abstention_rate", "topic_fatigue_suppressions", "topic_reentry_turns", "average_prompt_tokens", "average_working_memory_words", "stage_failure_distribution", "frequency_distribution", "connection_path_usage", "should_recall_hit_rate", "should_not_recall_leakage", "must_not_speak_leakage"]
    names = list(named_results)
    lines = ["# Governance Evaluation Comparison", "", "| Metric | " + " | ".join(names) + " |", "|---|" + "---:|" * len(names)]
    for metric in metrics:
        values = ["N/A" if named_results[n].get(metric) is None else json.dumps(named_results[n].get(metric), ensure_ascii=False, sort_keys=True) for n in names]
        lines.append(f"| {metric.replace('_', ' ').title()} | " + " | ".join(values) + " |")
    lines.extend(["", "Unannotated observations are excluded from all expectation denominators.", ""])
    return "\n".join(lines)
