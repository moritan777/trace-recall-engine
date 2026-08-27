from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _input_text(row: Mapping[str, Any]) -> str | None:
    for key in ("user", "input", "utterance", "text"):
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    conversation = _dict(row.get("conversation"))
    for key in ("user", "input", "utterance", "text"):
        value = conversation.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _recall(row: Mapping[str, Any]) -> dict[str, Any]:
    return _dict(row.get("recall"))


def _selected_words(row: Mapping[str, Any]) -> list[str]:
    return [str(value) for value in _list(_recall(row).get("selected_words"))]


def _selected_groups(row: Mapping[str, Any]) -> list[str]:
    result = []
    for value in _list(_recall(row).get("selected_thread_groups")):
        if isinstance(value, str):
            result.append(value)
        elif isinstance(value, dict):
            result.append(str(value.get("id") or value.get("group") or value))
        else:
            result.append(str(value))
    return result


def _candidates(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    analysis = _dict(_recall(row).get("activation_analysis"))
    return [dict(value) for value in _list(analysis.get("candidates")) if isinstance(value, dict)]


def _candidate_word(candidate: Mapping[str, Any]) -> str:
    return str(candidate.get("word") or candidate.get("identifier") or candidate.get("id") or "")


def _candidate_map(row: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {_candidate_word(candidate): candidate for candidate in _candidates(row) if _candidate_word(candidate)}


def _candidate_summary(row: Mapping[str, Any], limit: int = 12) -> list[dict[str, Any]]:
    result = []
    for candidate in _candidates(row)[:limit]:
        result.append(
            {
                "word": _candidate_word(candidate),
                "rank": candidate.get("rank"),
                "score": candidate.get("score"),
                "best_depth": candidate.get("best_depth"),
                "frequency": candidate.get("frequency"),
            }
        )
    return result


def _precision(row: Mapping[str, Any]) -> float | None:
    evaluation = _dict(row.get("evaluation"))
    for key in ("working_memory_recall_precision", "precision_like", "recall_precision"):
        value = evaluation.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return None


def _direct_words(row: Mapping[str, Any]) -> set[str]:
    words = set()
    for candidate in _candidates(row):
        try:
            depth = int(candidate.get("best_depth", -1))
        except (TypeError, ValueError):
            continue
        if depth == 0:
            word = _candidate_word(candidate)
            if word:
                words.add(word)
    return words


def compare_turn(base: Mapping[str, Any], virtual: Mapping[str, Any]) -> dict[str, Any]:
    turn = int(base.get("turn", virtual.get("turn", 0)) or 0)
    base_selected = set(_selected_words(base))
    virtual_selected = set(_selected_words(virtual))
    base_groups = _selected_groups(base)
    virtual_groups = _selected_groups(virtual)
    base_direct = _direct_words(base)
    virtual_direct = _direct_words(virtual)
    shared_direct = base_direct & virtual_direct
    base_candidates = _candidate_map(base)
    virtual_candidates = _candidate_map(virtual)

    categories: list[str] = []
    if base_selected != virtual_selected:
        categories.append("SELECTION_CHANGED")
    if base_selected and not virtual_selected:
        categories.append("VIRTUAL_ABSTENTION_REGRESSION")
    if not base_selected and virtual_selected:
        categories.append("VIRTUAL_RECOVERY")
    if base_groups and not virtual_groups:
        categories.append("THREAD_GROUP_LOSS")
    if not base_groups and virtual_groups:
        categories.append("THREAD_GROUP_RECOVERY")

    direct_lost = sorted(word for word in shared_direct if word in base_selected and word not in virtual_selected)
    direct_recovered = sorted(word for word in shared_direct if word not in base_selected and word in virtual_selected)
    direct_unselected = sorted(word for word in virtual_direct if word not in virtual_selected)
    if direct_lost:
        categories.append("DIRECT_INPUT_SELECTION_LOSS")
    if direct_recovered:
        categories.append("DIRECT_INPUT_SELECTION_RECOVERY")
    if direct_unselected:
        categories.append("DIRECT_INPUT_PRESENT_BUT_UNSELECTED")

    base_top_score = 0.0
    virtual_top_score = 0.0
    if _candidates(base):
        try:
            base_top_score = float(_candidates(base)[0].get("score", 0.0) or 0.0)
        except (TypeError, ValueError):
            pass
    if _candidates(virtual):
        try:
            virtual_top_score = float(_candidates(virtual)[0].get("score", 0.0) or 0.0)
        except (TypeError, ValueError):
            pass
    if base_top_score > 0 and virtual_top_score > 0 and base_top_score / virtual_top_score >= 10.0:
        categories.append("TOP_SCORE_COLLAPSED_10X")

    rank_shifts = []
    for word in sorted(base_candidates.keys() & virtual_candidates.keys()):
        try:
            base_rank = int(base_candidates[word].get("rank"))
            virtual_rank = int(virtual_candidates[word].get("rank"))
        except (TypeError, ValueError):
            continue
        shift = base_rank - virtual_rank
        if abs(shift) >= 5:
            rank_shifts.append({"word": word, "base_rank": base_rank, "virtual_rank": virtual_rank, "virtual_improvement": shift})
    if rank_shifts:
        categories.append("LARGE_RANK_SHIFT")

    base_precision = _precision(base)
    virtual_precision = _precision(virtual)
    precision_delta = None if base_precision is None or virtual_precision is None else virtual_precision - base_precision
    if precision_delta is not None:
        if precision_delta <= -0.25:
            categories.append("PRECISION_REGRESSION")
        elif precision_delta >= 0.25:
            categories.append("PRECISION_RECOVERY")

    union = base_selected | virtual_selected
    jaccard = 1.0 if not union else len(base_selected & virtual_selected) / len(union)

    return {
        "turn": turn,
        "input": _input_text(virtual) or _input_text(base),
        "categories": sorted(set(categories)),
        "base_selected_words": sorted(base_selected),
        "virtual_selected_words": sorted(virtual_selected),
        "base_selected_thread_groups": base_groups,
        "virtual_selected_thread_groups": virtual_groups,
        "base_direct_words": sorted(base_direct),
        "virtual_direct_words": sorted(virtual_direct),
        "direct_lost": direct_lost,
        "direct_recovered": direct_recovered,
        "direct_unselected": direct_unselected,
        "selection_jaccard": jaccard,
        "base_precision": base_precision,
        "virtual_precision": virtual_precision,
        "precision_delta": precision_delta,
        "base_top_score": base_top_score,
        "virtual_top_score": virtual_top_score,
        "rank_shifts": sorted(rank_shifts, key=lambda value: (-abs(value["virtual_improvement"]), value["word"]))[:10],
        "base_top_candidates": _candidate_summary(base),
        "virtual_top_candidates": _candidate_summary(virtual),
    }


def analyze(base_rows: Iterable[Mapping[str, Any]], virtual_rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    base_by_turn = {int(row.get("turn", 0) or 0): row for row in base_rows if int(row.get("turn", 0) or 0) > 0}
    virtual_by_turn = {int(row.get("turn", 0) or 0): row for row in virtual_rows if int(row.get("turn", 0) or 0) > 0}
    shared_turns = sorted(base_by_turn.keys() & virtual_by_turn.keys())
    comparisons = [compare_turn(base_by_turn[turn], virtual_by_turn[turn]) for turn in shared_turns]
    counts = Counter(category for row in comparisons for category in row["categories"])
    changed = [row for row in comparisons if row["categories"]]
    return {
        "shared_turn_count": len(shared_turns),
        "changed_turn_count": len(changed),
        "category_counts": dict(sorted(counts.items())),
        "comparisons": comparisons,
    }


def select_review_cases(comparisons: list[Mapping[str, Any]], limit: int = 30) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    buckets: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in comparisons:
        for category in row.get("categories", []):
            buckets[str(category)].append(row)

    selected: dict[int, dict[str, Any]] = {}
    category_order = [
        "PRECISION_REGRESSION",
        "VIRTUAL_ABSTENTION_REGRESSION",
        "THREAD_GROUP_LOSS",
        "DIRECT_INPUT_SELECTION_LOSS",
        "DIRECT_INPUT_PRESENT_BUT_UNSELECTED",
        "PRECISION_RECOVERY",
        "VIRTUAL_RECOVERY",
        "THREAD_GROUP_RECOVERY",
        "DIRECT_INPUT_SELECTION_RECOVERY",
        "LARGE_RANK_SHIFT",
        "TOP_SCORE_COLLAPSED_10X",
        "SELECTION_CHANGED",
    ]

    for category in category_order:
        rows = buckets.get(category, [])
        if not rows:
            continue
        picks = rows if len(rows) <= 4 else [rows[0], rows[len(rows) // 3], rows[(2 * len(rows)) // 3], rows[-1]]
        for row in picks:
            turn = int(row["turn"])
            if turn not in selected:
                selected[turn] = dict(row)
            if len(selected) >= limit:
                break
        if len(selected) >= limit:
            break

    if len(selected) < limit:
        for row in comparisons:
            if not row.get("categories"):
                continue
            turn = int(row["turn"])
            selected.setdefault(turn, dict(row))
            if len(selected) >= limit:
                break
    return [selected[turn] for turn in sorted(selected)]


def render_markdown(summary: Mapping[str, Any], review_cases: list[Mapping[str, Any]], focus_turns: list[int]) -> str:
    lines = [
        "# Long-Horizon Recall Failure Pattern Analysis",
        "",
        "Offline comparison only. No recall policy, decay, gate, threshold, or propagation rule is changed.",
        "",
        f"- Shared turns: {summary['shared_turn_count']}",
        f"- Changed turns: {summary['changed_turn_count']}",
        "",
        "## Category counts",
        "",
        "| Category | Count |",
        "|---|---:|",
    ]
    for category, count in summary["category_counts"].items():
        lines.append(f"| {category} | {count} |")

    lines.extend([
        "",
        "## Representative review cases",
        "",
        "| Turn | Categories | Base selected | Virtual selected | Direct words | Jaccard | Precision delta |",
        "|---:|---|---|---|---|---:|---:|",
    ])
    for row in review_cases:
        delta = row.get("precision_delta")
        delta_text = "N/A" if delta is None else f"{float(delta):.3f}"
        lines.append(
            f"| {row['turn']} | {', '.join(row['categories'])} | "
            f"{', '.join(row['base_selected_words']) or '-'} | {', '.join(row['virtual_selected_words']) or '-'} | "
            f"{', '.join(row['virtual_direct_words']) or '-'} | {float(row['selection_jaccard']):.3f} | {delta_text} |"
        )

    by_turn = {int(row["turn"]): row for row in summary["comparisons"]}
    if focus_turns:
        lines.extend(["", "## Focus turns", ""])
        for turn in focus_turns:
            row = by_turn.get(turn)
            if row is None:
                lines.extend([f"### Turn {turn}", "", "Not present in both logs.", ""])
                continue
            lines.extend([
                f"### Turn {turn}",
                "",
                f"- Input: `{row.get('input')}`",
                f"- Categories: `{', '.join(row['categories']) or 'NONE'}`",
                f"- Base selected: `{row['base_selected_words']}`",
                f"- Virtual selected: `{row['virtual_selected_words']}`",
                f"- Virtual direct words: `{row['virtual_direct_words']}`",
                f"- Direct present but unselected: `{row['direct_unselected']}`",
                f"- Rank shifts: `{json.dumps(row['rank_shifts'], ensure_ascii=False)}`",
                "",
            ])

    lines.extend([
        "## Interpretation boundary",
        "",
        "This report identifies recurring structural symptoms only. It does not infer semantic importance, does not label any word as a special cue, and does not recommend a production fix from a single example.",
        "",
    ])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare baseline and virtual-time Research Logger JSONL files without changing runtime behavior.")
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--virtual", required=True, type=Path)
    parser.add_argument("--json", required=True, type=Path)
    parser.add_argument("--markdown", required=True, type=Path)
    parser.add_argument("--review-jsonl", required=True, type=Path)
    parser.add_argument("--review-limit", type=int, default=30)
    parser.add_argument("--focus-turn", action="append", type=int, default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = analyze(read_jsonl(args.base), read_jsonl(args.virtual))
    review_cases = select_review_cases(summary["comparisons"], args.review_limit)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.review_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    args.markdown.write_text(render_markdown(summary, review_cases, args.focus_turn), encoding="utf-8")
    with args.review_jsonl.open("w", encoding="utf-8") as handle:
        for row in review_cases:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"shared_turns={summary['shared_turn_count']}")
    print(f"changed_turns={summary['changed_turn_count']}")
    print(f"review_cases={len(review_cases)}")
    for category, count in summary["category_counts"].items():
        print(f"{category}={count}")
    print(f"json={args.json}")
    print(f"markdown={args.markdown}")
    print(f"review_jsonl={args.review_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
