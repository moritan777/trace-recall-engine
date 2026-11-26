#!/usr/bin/env python3
"""Enrich Human-Valid evaluation CSV with evidence from the existing fixture.

No Trace Recall Engine changes are made. This is offline post-processing.

Evidence selection is intentionally conservative and provenance-first:
- only turns BEFORE the evaluated turn can be selected;
- only fixture turns (learn by default) are evidence;
- source text is copied verbatim, never semantically rewritten;
- expected/unexpected terms are used as search keys only;
- Working Memory terms may optionally help FIND source turns, but are never facts themselves;
- a short recent-history window is included to preserve conversational context.

Usage:
  python enrich_human_valid_history.py \
    eval_conversations/long_100t_mixed_recall.jsonl \
    run/human_valid_100.csv \
    -o run/human_valid_100_with_history.csv

Useful options:
  --max-facts 8
  --recent-learn 2
  --no-working-memory-keys
  --candidate-audit run/human_valid_history_audit.jsonl
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{no}: invalid JSON: {exc}") from exc
        if not isinstance(item, dict):
            raise SystemExit(f"{path}:{no}: expected JSON object")
        rows.append(item)
    return rows


def load_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit(f"{path}: missing CSV header")
        return list(reader), list(reader.fieldnames)


def parse_json_cell(value: str | None, default: Any) -> Any:
    if value is None or not value.strip():
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def norm(text: str) -> str:
    return "".join(str(text).casefold().split())


def useful_key(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("word") or value.get("text") or value.get("surface")
    if value is None:
        return None
    s = str(value).strip()
    # One-character fragments are too noisy as evidence selectors. Two ASCII
    # letters/numbers remain useful (SF, AI, dates etc.).
    if len(s) < 2:
        return None
    return s


def collect_keys(row: dict[str, str], use_wm: bool) -> dict[str, set[str]]:
    groups: dict[str, set[str]] = {"expected": set(), "unexpected": set(), "working_memory": set()}
    for column, group in (("expected_words", "expected"), ("unexpected_words", "unexpected")):
        for value in parse_json_cell(row.get(column), []):
            key = useful_key(value)
            if key:
                groups[group].add(key)
    if use_wm:
        for value in parse_json_cell(row.get("working_memory_words"), []):
            key = useful_key(value)
            if key:
                groups["working_memory"].add(key)
    return groups


def source_text(item: dict[str, Any]) -> str:
    for key in ("user", "text", "input_text", "content"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def score_candidate(text: str, keys: dict[str, set[str]]) -> tuple[int, list[str]]:
    ntext = norm(text)
    reasons: list[str] = []
    score = 0
    weights = {"expected": 6, "unexpected": 5, "working_memory": 2}
    for group, terms in keys.items():
        matched = sorted({term for term in terms if norm(term) and norm(term) in ntext})
        if matched:
            score += weights[group] * len(matched)
            reasons.extend(f"{group}:{term}" for term in matched)
    return score, reasons


def select_history(
    fixture: list[dict[str, Any]],
    turn: int,
    keys: dict[str, set[str]],
    max_facts: int,
    recent_learn: int,
    learn_only: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    prior = []
    for item in fixture:
        try:
            t = int(item.get("turn"))
        except (TypeError, ValueError):
            continue
        if t >= turn:
            continue  # hard anti-leak boundary
        if learn_only and str(item.get("mode", "")) != "learn":
            continue
        text = source_text(item)
        if text:
            prior.append((t, text, item))

    ranked: list[dict[str, Any]] = []
    for t, text, item in prior:
        score, reasons = score_candidate(text, keys)
        if score:
            ranked.append({
                "turn": t,
                "text": text,
                "mode": item.get("mode", ""),
                "score": score,
                "reasons": reasons,
                "selection": "keyword",
            })
    ranked.sort(key=lambda x: (-x["score"], -x["turn"]))

    selected = ranked[:max_facts]
    selected_turns = {x["turn"] for x in selected}

    # Add a small amount of recent learn context. It is explicitly marked as
    # context, not a semantic match, so reviewers can distinguish provenance.
    if recent_learn:
        for t, text, item in reversed(prior[-recent_learn:]):
            if t in selected_turns:
                continue
            selected.append({
                "turn": t,
                "text": text,
                "mode": item.get("mode", ""),
                "score": 0,
                "reasons": ["recent_context"],
                "selection": "recent_context",
            })
            selected_turns.add(t)

    # Present evidence chronologically to the human evaluator.
    selected.sort(key=lambda x: x["turn"])
    return selected, ranked


def fact_cell(selected: list[dict[str, Any]]) -> str:
    # Keep only source evidence and selection provenance in the evaluation CSV.
    # No subject/relation/object interpretation is fabricated here.
    evidence = [
        {
            "turn": x["turn"],
            "text": x["text"],
            "selection": x["selection"],
            "matched_by": x["reasons"],
        }
        for x in selected
    ]
    return json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fixture_jsonl", type=Path)
    ap.add_argument("human_valid_csv", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--max-facts", type=int, default=8)
    ap.add_argument("--recent-learn", type=int, default=2)
    ap.add_argument("--no-working-memory-keys", action="store_true")
    ap.add_argument("--all-prior-modes", action="store_true", help="allow prior ask turns too; default evidence is learn only")
    ap.add_argument("--candidate-audit", type=Path, help="optional JSONL of all matched candidates and reasons")
    args = ap.parse_args()

    fixture = load_jsonl(args.fixture_jsonl)
    rows, fieldnames = load_csv(args.human_valid_csv)
    required = {"turn", "user_input", "llm_response", "relevant_known_facts", "relevant_previous_turns"}
    missing = required - set(fieldnames)
    if missing:
        raise SystemExit(f"CSV missing required columns: {sorted(missing)}")

    audit_records: list[dict[str, Any]] = []
    nonempty = 0
    total_evidence = 0
    for row in rows:
        try:
            turn = int(row["turn"])
        except (TypeError, ValueError):
            raise SystemExit(f"invalid turn in CSV: {row.get('turn')!r}")
        keys = collect_keys(row, not args.no_working_memory_keys)
        selected, ranked = select_history(
            fixture, turn, keys, max(0, args.max_facts), max(0, args.recent_learn), not args.all_prior_modes
        )
        row["relevant_known_facts"] = fact_cell(selected)
        row["relevant_previous_turns"] = json.dumps([x["turn"] for x in selected], ensure_ascii=False)
        if selected:
            nonempty += 1
            total_evidence += len(selected)
        audit_records.append({
            "turn": turn,
            "search_keys": {k: sorted(v) for k, v in keys.items()},
            "selected": selected,
            "all_keyword_candidates": ranked,
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)

    if args.candidate_audit:
        args.candidate_audit.parent.mkdir(parents=True, exist_ok=True)
        with args.candidate_audit.open("w", encoding="utf-8", newline="\n") as f:
            for record in audit_records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"[done] rows={len(rows)} with_evidence={nonempty} evidence_items={total_evidence} output={args.output}")
    print("[safety] source_turn < evaluation_turn enforced; source text copied verbatim; no semantic facts invented")
    print("[note] keyword/WM terms select evidence only. They are not themselves treated as ground truth.")
    if args.candidate_audit:
        print(f"[audit] {args.candidate_audit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
