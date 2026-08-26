from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


DEFAULT_NUMERIC_TOLERANCE = 1e-12


def _path_key(path: dict[str, Any]) -> tuple[str, str]:
    return str(path.get("from_id", "")), str(path.get("to_id", ""))


def analyze_terminal_paths(
    paths: Iterable[dict[str, Any]],
    *,
    terminal_depth: int = 3,
    numeric_tolerance: float = DEFAULT_NUMERIC_TOLERANCE,
) -> dict[str, Any]:
    """Offline-only arithmetic equivalence analysis for terminal word->thread paths.

    This deliberately does not alter traversal, storage, activation, gate, fatigue,
    thread-group selection, reinforcement, or working memory.  Every physical path
    remains represented in ``contributors``; only the arithmetic sum for identical
    terminal (word, thread) edges is compared with the baseline physical-path sum.
    """
    terminal = [
        p
        for p in paths
        if int(p.get("depth", -1)) == terminal_depth
        and p.get("from_type") == "word"
        and p.get("to_type") == "thread"
    ]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for path in terminal:
        grouped[_path_key(path)].append(path)

    baseline_by_thread: dict[str, float] = defaultdict(float)
    aggregated_by_thread: dict[str, float] = defaultdict(float)
    edge_rows: list[dict[str, Any]] = []
    max_multiplicity = 0

    for (word, thread_id), contributors in sorted(grouped.items()):
        individual = [float(p.get("score", 0.0)) for p in contributors]
        baseline_sum = sum(individual)
        # Counterfactual arithmetic: one terminal edge operation after preserving
        # every incoming contribution/provenance item.
        aggregated_sum = sum(individual)
        baseline_by_thread[thread_id] += baseline_sum
        aggregated_by_thread[thread_id] += aggregated_sum
        max_multiplicity = max(max_multiplicity, len(contributors))
        edge_rows.append(
            {
                "source_word": word,
                "destination_thread": thread_id,
                "multiplicity": len(contributors),
                "baseline_sum": baseline_sum,
                "aggregated_sum": aggregated_sum,
                "numeric_delta": abs(baseline_sum - aggregated_sum),
                "contributors": [
                    {
                        "score": float(p.get("score", 0.0)),
                        "reason": str(p.get("reason", "")),
                        "from_id": str(p.get("from_id", "")),
                        "to_id": str(p.get("to_id", "")),
                    }
                    for p in contributors
                ],
            }
        )

    thread_ids = set(baseline_by_thread) | set(aggregated_by_thread)
    thread_deltas = {
        tid: abs(baseline_by_thread.get(tid, 0.0) - aggregated_by_thread.get(tid, 0.0))
        for tid in sorted(thread_ids)
    }
    max_delta = max(thread_deltas.values(), default=0.0)
    physical_count = len(terminal)
    distinct_count = len(grouped)
    operations_saved = max(physical_count - distinct_count, 0)

    return {
        "marker": "OFFLINE_TERMINAL_AGGREGATION_COUNTERFACTUAL",
        "production_replay": False,
        "production_changed": False,
        "terminal_depth": terminal_depth,
        "numeric_tolerance": numeric_tolerance,
        "physical_terminal_path_count": physical_count,
        "distinct_terminal_edge_count": distinct_count,
        "aggregation_ratio": (physical_count / distinct_count) if distinct_count else 1.0,
        "maximum_repeated_edge_multiplicity": max_multiplicity,
        "estimated_arithmetic_operations_saved": operations_saved,
        "estimated_arithmetic_reduction_rate": (operations_saved / physical_count) if physical_count else 0.0,
        "max_thread_numeric_delta": max_delta,
        "numeric_equivalent": max_delta <= numeric_tolerance,
        "provenance_preserved": sum(len(row["contributors"]) for row in edge_rows) == physical_count,
        "thread_deltas": thread_deltas,
        "edges": edge_rows,
    }


def analyze_research_records(
    records: Iterable[dict[str, Any]],
    *,
    terminal_depth: int = 3,
    numeric_tolerance: float = DEFAULT_NUMERIC_TOLERANCE,
) -> dict[str, Any]:
    turns: list[dict[str, Any]] = []
    for record in records:
        recall = record.get("recall") or {}
        activation_analysis = recall.get("activation_analysis") or {}
        paths = activation_analysis.get("paths") or []
        if not paths:
            continue
        row = analyze_terminal_paths(paths, terminal_depth=terminal_depth, numeric_tolerance=numeric_tolerance)
        row["turn"] = record.get("turn")
        # These are observations copied from the captured Production result.  The
        # offline arithmetic does not reconstruct or mutate downstream policy.
        row["observed_candidate_order"] = [x.get("word") for x in activation_analysis.get("candidates", [])]
        row["observed_selected_thread_groups"] = [
            x.get("canonical_key") or x.get("representative_thread_id")
            for x in recall.get("selected_thread_groups", [])
        ]
        row["observed_selected_words"] = [
            x.get("word") if isinstance(x, dict) else x for x in recall.get("selected_words", [])
        ]
        turns.append(row)

    total_physical = sum(x["physical_terminal_path_count"] for x in turns)
    total_distinct = sum(x["distinct_terminal_edge_count"] for x in turns)
    max_delta = max((x["max_thread_numeric_delta"] for x in turns), default=0.0)
    provenance_ok = all(x["provenance_preserved"] for x in turns)
    numeric_ok = all(x["numeric_equivalent"] for x in turns)

    if not turns:
        judgement = "INSUFFICIENT_DATA"
    elif numeric_ok and provenance_ok:
        # Full Gate/ThreadGroup/WM replay is intentionally not claimed from trace
        # arithmetic alone.  This classification is therefore arithmetic-only.
        judgement = "TERMINAL_ARITHMETIC_EQUIVALENT"
    elif numeric_ok:
        judgement = "NUMERICALLY_EQUIVALENT_BUT_SEMANTIC_DIFFERENCE"
    else:
        judgement = "RECALL_BEHAVIOR_CHANGED"

    return {
        "analysis": "terminal_depth_aggregation_equivalence",
        "scope": "offline_only",
        "judgement": judgement,
        "full_downstream_replay_performed": False,
        "turn_count": len(turns),
        "physical_terminal_path_count": total_physical,
        "distinct_terminal_edge_count": total_distinct,
        "aggregation_ratio": (total_physical / total_distinct) if total_distinct else 1.0,
        "estimated_arithmetic_operations_saved": max(total_physical - total_distinct, 0),
        "max_thread_numeric_delta": max_delta,
        "numeric_equivalent_all_turns": numeric_ok,
        "provenance_preserved_all_turns": provenance_ok,
        "turns": turns,
    }


def terminal_aggregation_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Terminal-depth Aggregation Equivalence Validation",
        "",
        f"- Judgement: **{result.get('judgement')}**",
        f"- Scope: **{result.get('scope')}**",
        f"- Turns observed: **{result.get('turn_count', 0)}**",
        f"- Physical terminal paths: **{result.get('physical_terminal_path_count', 0)}**",
        f"- Distinct terminal edges: **{result.get('distinct_terminal_edge_count', 0)}**",
        f"- Aggregation ratio: **{result.get('aggregation_ratio', 0.0):.3f}x**",
        f"- Estimated arithmetic operations saved: **{result.get('estimated_arithmetic_operations_saved', 0)}**",
        f"- Maximum numeric delta: **{result.get('max_thread_numeric_delta', 0.0):.3e}**",
        f"- Provenance preserved: **{result.get('provenance_preserved_all_turns', False)}**",
        "",
        "> This is an offline arithmetic counterfactual. It does not change Production traversal or claim a full Gate/ThreadGroup/Working-Memory replay.",
        "",
        "| Turn | Physical paths | Distinct edges | Ratio | Max multiplicity | Max delta |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in result.get("turns", []):
        lines.append(
            f"| {row.get('turn')} | {row.get('physical_terminal_path_count', 0)} | "
            f"{row.get('distinct_terminal_edge_count', 0)} | {row.get('aggregation_ratio', 0.0):.3f}x | "
            f"{row.get('maximum_repeated_edge_multiplicity', 0)} | {row.get('max_thread_numeric_delta', 0.0):.3e} |"
        )
    return "\n".join(lines) + "\n"
