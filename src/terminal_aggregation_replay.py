from __future__ import annotations

import argparse
import json
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator

from threaded_concept_memory_probe import (
    ActivatedThread,
    ActivatedWord,
    ActivationGate,
    ActivationResult,
    ActivationTrace,
    GatedContext,
)
from trace_recall.extractors import ExtractedWord
from trace_recall.terminal_aggregation import DEFAULT_NUMERIC_TOLERANCE, analyze_terminal_paths


class _ReplayFatigueStore:
    """Minimal read-only store facade for replaying captured fatigue decisions."""

    def __init__(self, fatigue: dict[str, int]) -> None:
        self.fatigue = fatigue

    def get_fatigue_prompt(self, word: str, recent_turns: int) -> int:
        return int(self.fatigue.get(word, 0))

    def get_fatigue_response(self, word: str, recent_turns: int) -> int:
        return 0


def iter_research_records(path: str | Path) -> Iterator[dict[str, Any]]:
    """Stream a JSONL research log, optionally from a ZIP containing one JSONL."""
    source = Path(path)
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            members = [name for name in archive.namelist() if name.lower().endswith(".jsonl")]
            if len(members) != 1:
                raise ValueError(f"expected exactly one JSONL member in {source}, found {len(members)}")
            with archive.open(members[0]) as handle:
                for raw in handle:
                    raw = raw.strip()
                    if raw:
                        yield json.loads(raw)
        return

    with source.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def _input_words(record: dict[str, Any]) -> list[ExtractedWord]:
    payload = (record.get("extractor") or {}).get("normalized_words") or []
    return [
        ExtractedWord(str(item.get("word", "")), float(item.get("weight", 1.0)))
        for item in payload
        if item.get("word")
    ]


def _fatigue_map(record: dict[str, Any]) -> dict[str, int]:
    """Recover only the fatigue values needed to replay captured Gate decisions.

    Selected non-reentry words can safely use zero because their observed fatigue was
    below threshold. Explicit re-entry words are pinned to the captured threshold.
    Suppressed fatigue values are recovered from stage diagnostics when available.
    No new runtime fatigue policy is inferred here.
    """
    recall = record.get("recall") or {}
    config = record.get("governance_observation_config") or {}
    threshold = int(config.get("fatigue_threshold", 3))
    result: dict[str, int] = {
        str(word): threshold for word in (recall.get("topic_reentry_words") or [])
    }
    for event in recall.get("stage_diagnostics") or []:
        if event.get("stage") != "ACTIVATION_GATE":
            continue
        word = str(event.get("identifier", ""))
        if not word:
            continue
        contribution = float(event.get("fatigue_contribution") or 0.0)
        if contribution < 0:
            result[word] = max(result.get(word, 0), int(round(-contribution)))
        elif event.get("reason") == "recently_exposed":
            result[word] = max(result.get(word, 0), threshold)
    return result


def _thread_components(
    paths: list[dict[str, Any]],
    *,
    aggregate_terminal: bool,
    terminal_depth: int,
) -> tuple[dict[str, float], dict[str, float], dict[str, set[str]], dict[str, list[str]]]:
    base: dict[str, float] = defaultdict(float)
    bonus: dict[str, float] = defaultdict(float)
    matched: dict[str, set[str]] = defaultdict(set)
    activated_by: dict[str, list[str]] = defaultdict(list)
    terminal: dict[tuple[str, str], list[float]] = defaultdict(list)

    def remember_source(thread_id: str, word: str) -> None:
        matched[thread_id].add(word)
        tag = f"word:{word}"
        if tag not in activated_by[thread_id]:
            activated_by[thread_id].append(tag)

    for path in paths:
        from_type = path.get("from_type")
        to_type = path.get("to_type")
        reason = str(path.get("reason", ""))
        if from_type == "word" and to_type == "thread":
            word = str(path.get("from_id", ""))
            thread_id = str(path.get("to_id", ""))
            score = float(path.get("score", 0.0))
            if aggregate_terminal and int(path.get("depth", -1)) == terminal_depth:
                terminal[(word, thread_id)].append(score)
            else:
                base[thread_id] += score
                remember_source(thread_id, word)
        elif from_type == "thread" and to_type == "thread" and reason.startswith("common-bonus"):
            bonus[str(path.get("to_id", ""))] += float(path.get("score", 0.0))

    for (word, thread_id), contributions in terminal.items():
        # Sum every captured contribution; only the repeated terminal-edge arithmetic
        # is collapsed. Contributor count/provenance remains validated separately by
        # analyze_terminal_paths.
        base[thread_id] += sum(contributions)
        remember_source(thread_id, word)

    return base, bonus, matched, activated_by


def _build_activation(
    record: dict[str, Any],
    *,
    aggregate_terminal: bool,
    terminal_depth: int,
) -> ActivationResult:
    recall = record.get("recall") or {}
    analysis = recall.get("activation_analysis") or {}
    paths = analysis.get("paths") or []

    activated_words = [
        ActivatedWord(
            word=str(item.get("word", "")),
            score=float(item.get("score", 0.0)),
            best_depth=int(item.get("best_depth", 99)),
            thread_ids=list(item.get("thread_ids") or []),
            activated_by=list(item.get("activation_sources") or []),
        )
        for item in analysis.get("candidates") or []
        if item.get("word")
    ]

    base, bonus, matched, activated_by = _thread_components(
        paths,
        aggregate_terminal=aggregate_terminal,
        terminal_depth=terminal_depth,
    )
    thread_meta = analysis.get("threads") or {}
    activated_threads: list[ActivatedThread] = []
    for thread_id in recall.get("activated_threads") or []:
        thread_id = str(thread_id)
        meta = thread_meta.get(thread_id) or {}
        activated_threads.append(
            ActivatedThread(
                thread_id=thread_id,
                score=float(base.get(thread_id, 0.0) + bonus.get(thread_id, 0.0)),
                base_score=float(base.get(thread_id, 0.0)),
                common_bonus=float(bonus.get(thread_id, 0.0)),
                words=list(meta.get("words") or []),
                matched_words=sorted(matched.get(thread_id, set())),
                activated_by=list(activated_by.get(thread_id, []))[:8],
                date=str(meta.get("date", "")),
                canonical_key=str(meta.get("canonical_key", "")),
                thread_strength=float(meta.get("strength", 1.0)),
                effective_strength=1.0,
                same_key_thread_count=1,
                created_by=str(meta.get("created_by", "user")),
            )
        )

    traces = [
        ActivationTrace(
            str(path.get("from_type", "")),
            str(path.get("from_id", "")),
            str(path.get("to_type", "")),
            str(path.get("to_id", "")),
            int(path.get("depth", 0)),
            float(path.get("score", 0.0)),
            str(path.get("reason", "")),
        )
        for path in paths
    ]
    return ActivationResult(_input_words(record), activated_words, activated_threads, traces)


def _gate(record: dict[str, Any], activation: ActivationResult) -> GatedContext:
    config = record.get("governance_observation_config") or {}
    gate = ActivationGate(
        min_word_score=float(config.get("gate_min_word_score", 0.05)),
        store=_ReplayFatigueStore(_fatigue_map(record)),
        fatigue_recent_turns=int(config.get("fatigue_recent_turns", 10)),
        fatigue_threshold=int(config.get("fatigue_threshold", 3)),
        diagnostics=None,
    )
    return gate.gate(activation)


def _group_signature(group: Any) -> dict[str, Any]:
    return {
        "canonical_key": group.canonical_key,
        "representative_thread_id": group.representative_thread_id,
        "member_thread_ids": list(group.member_thread_ids),
        "words": list(group.words),
        "direct_words": list(group.direct_words),
        "core_words": list(group.core_words),
        "support_words": list(group.support_words),
        "suppressed_words": list(group.suppressed_words),
    }


def _gate_signature(gated: GatedContext) -> dict[str, Any]:
    return {
        "selected_thread_groups": [_group_signature(group) for group in gated.threads],
        "gated_words": [word.word for word in gated.words],
        "suppressed_words": [word.word for word in gated.suppressed_words],
        "working_memory_words": [word.word for word in gated.words],
        "outcome": gated.outcome,
        "topic_reentry_words": list(gated.topic_reentry_words or []),
    }


def _thread_score_delta(baseline: ActivationResult, aggregated: ActivationResult) -> float:
    left = {thread.thread_id: thread.score for thread in baseline.activated_threads}
    right = {thread.thread_id: thread.score for thread in aggregated.activated_threads}
    return max(
        (abs(left.get(key, 0.0) - right.get(key, 0.0)) for key in set(left) | set(right)),
        default=0.0,
    )


def _observation_fidelity(record: dict[str, Any], replay: GatedContext) -> dict[str, bool]:
    recall = record.get("recall") or {}
    working_memory = record.get("working_memory") or {}
    observed_groups = [
        item.get("canonical_key") if isinstance(item, dict) else item
        for item in (recall.get("selected_thread_groups") or [])
    ]
    return {
        "selected_group_order": observed_groups == [group.canonical_key for group in replay.threads],
        "working_memory_word_set": set(working_memory.get("selected_words") or [])
        == {word.word for word in replay.words},
        "suppressed_word_order": list(recall.get("fatigue_suppressed_words") or [])
        == [word.word for word in replay.suppressed_words],
        "outcome": recall.get("outcome") == replay.outcome,
        "topic_reentry_words": list(recall.get("topic_reentry_words") or [])
        == list(replay.topic_reentry_words or []),
    }


def analyze_downstream_replay(
    records: Iterable[dict[str, Any]],
    *,
    terminal_depth: int = 3,
    numeric_tolerance: float = DEFAULT_NUMERIC_TOLERANCE,
) -> dict[str, Any]:
    turns: list[dict[str, Any]] = []
    total_physical = 0
    total_distinct = 0
    max_numeric_delta = 0.0
    fidelity_counts: dict[str, int] = defaultdict(int)

    for record in records:
        paths = ((record.get("recall") or {}).get("activation_analysis") or {}).get("paths") or []
        if not paths:
            continue

        arithmetic = analyze_terminal_paths(
            paths,
            terminal_depth=terminal_depth,
            numeric_tolerance=numeric_tolerance,
        )
        baseline = _build_activation(record, aggregate_terminal=False, terminal_depth=terminal_depth)
        aggregated = _build_activation(record, aggregate_terminal=True, terminal_depth=terminal_depth)
        baseline_gate = _gate(record, baseline)
        aggregated_gate = _gate(record, aggregated)
        baseline_signature = _gate_signature(baseline_gate)
        aggregated_signature = _gate_signature(aggregated_gate)
        score_delta = _thread_score_delta(baseline, aggregated)
        fidelity = _observation_fidelity(record, baseline_gate)
        for key, ok in fidelity.items():
            fidelity_counts[key] += int(ok)

        turn = {
            "turn": record.get("turn"),
            "physical_terminal_path_count": arithmetic["physical_terminal_path_count"],
            "distinct_terminal_edge_count": arithmetic["distinct_terminal_edge_count"],
            "aggregation_ratio": arithmetic["aggregation_ratio"],
            "maximum_repeated_edge_multiplicity": arithmetic["maximum_repeated_edge_multiplicity"],
            "max_thread_numeric_delta": max(arithmetic["max_thread_numeric_delta"], score_delta),
            "numeric_equivalent": arithmetic["numeric_equivalent"] and score_delta <= numeric_tolerance,
            "provenance_preserved": arithmetic["provenance_preserved"],
            "candidate_order_equal": [word.word for word in baseline.activated_words]
            == [word.word for word in aggregated.activated_words],
            "activated_thread_order_equal": [thread.thread_id for thread in baseline.activated_threads]
            == [thread.thread_id for thread in aggregated.activated_threads],
            "selected_thread_groups_equal": baseline_signature["selected_thread_groups"]
            == aggregated_signature["selected_thread_groups"],
            "gate_words_equal": baseline_signature["gated_words"] == aggregated_signature["gated_words"],
            "suppressed_words_equal": baseline_signature["suppressed_words"]
            == aggregated_signature["suppressed_words"],
            "working_memory_words_equal": baseline_signature["working_memory_words"]
            == aggregated_signature["working_memory_words"],
            "outcome_equal": baseline_signature["outcome"] == aggregated_signature["outcome"],
            "topic_reentry_equal": baseline_signature["topic_reentry_words"]
            == aggregated_signature["topic_reentry_words"],
            "downstream_discrete_equal": baseline_signature == aggregated_signature,
            "baseline_observation_fidelity": fidelity,
        }
        total_physical += arithmetic["physical_terminal_path_count"]
        total_distinct += arithmetic["distinct_terminal_edge_count"]
        max_numeric_delta = max(max_numeric_delta, turn["max_thread_numeric_delta"])
        turns.append(turn)

    numeric_ok = all(turn["numeric_equivalent"] for turn in turns)
    provenance_ok = all(turn["provenance_preserved"] for turn in turns)
    downstream_ok = all(turn["downstream_discrete_equal"] for turn in turns)

    if not turns:
        judgement = "INSUFFICIENT_DATA"
    elif numeric_ok and provenance_ok and downstream_ok:
        judgement = "TERMINAL_AGGREGATION_DOWNSTREAM_EQUIVALENT"
    elif numeric_ok and provenance_ok:
        judgement = "NUMERICALLY_EQUIVALENT_BUT_DOWNSTREAM_CHANGED"
    elif numeric_ok:
        judgement = "NUMERICALLY_EQUIVALENT_BUT_SEMANTIC_DIFFERENCE"
    else:
        judgement = "RECALL_BEHAVIOR_CHANGED"

    return {
        "analysis": "terminal_depth_aggregation_full_downstream_replay",
        "scope": "offline_only",
        "production_changed": False,
        "judgement": judgement,
        "full_downstream_replay_performed": True,
        "turn_count": len(turns),
        "physical_terminal_path_count": total_physical,
        "distinct_terminal_edge_count": total_distinct,
        "aggregation_ratio": (total_physical / total_distinct) if total_distinct else 1.0,
        "estimated_arithmetic_operations_saved": max(total_physical - total_distinct, 0),
        "estimated_arithmetic_reduction_rate": (
            (total_physical - total_distinct) / total_physical if total_physical else 0.0
        ),
        "max_numeric_delta": max_numeric_delta,
        "numeric_equivalent_all_turns": numeric_ok,
        "provenance_preserved_all_turns": provenance_ok,
        "downstream_equivalent_all_turns": downstream_ok,
        "baseline_observation_fidelity_counts": dict(fidelity_counts),
        "turns": turns,
    }


def replay_markdown(result: dict[str, Any]) -> str:
    turn_count = int(result.get("turn_count", 0))
    lines = [
        "# Terminal-depth Aggregation Full Downstream Replay",
        "",
        f"- Judgement: **{result.get('judgement')}**",
        f"- Scope: **{result.get('scope')}**",
        f"- Full downstream replay performed: **{result.get('full_downstream_replay_performed')}**",
        f"- Turns replayed: **{turn_count}**",
        f"- Physical terminal paths: **{result.get('physical_terminal_path_count', 0)}**",
        f"- Distinct terminal edges: **{result.get('distinct_terminal_edge_count', 0)}**",
        f"- Aggregation ratio: **{result.get('aggregation_ratio', 0.0):.3f}x**",
        f"- Estimated arithmetic reduction: **{100 * result.get('estimated_arithmetic_reduction_rate', 0.0):.2f}%**",
        f"- Maximum numeric delta: **{result.get('max_numeric_delta', 0.0):.3e}**",
        f"- Provenance preserved all turns: **{result.get('provenance_preserved_all_turns')}**",
        f"- Downstream equivalent all turns: **{result.get('downstream_equivalent_all_turns')}**",
        "",
        "## Baseline replay fidelity to captured Production observations",
        "",
    ]
    for key, count in sorted((result.get("baseline_observation_fidelity_counts") or {}).items()):
        lines.append(f"- {key}: **{count}/{turn_count}**")
    lines += [
        "",
        "> The replay reconstructs the captured ActivationResult and runs the current ActivationGate/ThreadGroup/Fatigue/Working-Memory selection twice: baseline physical terminal paths vs terminal-edge aggregation. Production storage and recall are not changed.",
        "",
        "| Turn | Physical | Distinct | Ratio | Numeric delta | Groups | Gate words | Suppressed | WM | Outcome | Re-entry |",
        "| ---: | ---: | ---: | ---: | ---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for row in result.get("turns", []):
        mark = lambda key: "✓" if row.get(key) else "✗"
        lines.append(
            f"| {row.get('turn')} | {row.get('physical_terminal_path_count')} | "
            f"{row.get('distinct_terminal_edge_count')} | {row.get('aggregation_ratio', 0.0):.3f}x | "
            f"{row.get('max_thread_numeric_delta', 0.0):.3e} | "
            f"{mark('selected_thread_groups_equal')} | {mark('gate_words_equal')} | "
            f"{mark('suppressed_words_equal')} | {mark('working_memory_words_equal')} | "
            f"{mark('outcome_equal')} | {mark('topic_reentry_equal')} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline full downstream replay for terminal-depth aggregation."
    )
    parser.add_argument("--research-log", required=True, help="Research Logger schema-v2 JSONL or ZIP containing one JSONL.")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--report-md", required=True)
    parser.add_argument("--terminal-depth", type=int, default=3)
    parser.add_argument("--numeric-tolerance", type=float, default=DEFAULT_NUMERIC_TOLERANCE)
    args = parser.parse_args()

    result = analyze_downstream_replay(
        iter_research_records(args.research_log),
        terminal_depth=args.terminal_depth,
        numeric_tolerance=args.numeric_tolerance,
    )
    Path(args.output_json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.report_md).write_text(replay_markdown(result), encoding="utf-8")

    print("judgement:", result["judgement"])
    print("turn_count:", result["turn_count"])
    print("physical_terminal_paths:", result["physical_terminal_path_count"])
    print("distinct_terminal_edges:", result["distinct_terminal_edge_count"])
    print("aggregation_ratio:", result["aggregation_ratio"])
    print("max_numeric_delta:", result["max_numeric_delta"])
    print("provenance_preserved:", result["provenance_preserved_all_turns"])
    print("downstream_equivalent:", result["downstream_equivalent_all_turns"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
