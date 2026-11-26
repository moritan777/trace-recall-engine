#!/usr/bin/env python3
"""Convert Trace Recall research JSONL into a Human-Valid evaluation CSV.

This script does NOT auto-judge Human-Valid classes. It extracts evidence and
leaves primary_class / flags / confidence / reason blank for blind human review.
After classification, recall-diagnostic columns are available in the same CSV.

Usage:
  python analyze_human_valid.py run/resp100-research.jsonl -o run/human_valid_100.csv
  python analyze_human_valid.py run/resp100-research.jsonl -o run/human_valid_100.csv --include-non-llm
"""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path
from typing import Any

CLASSES = (
    "VALID", "VALID_RECALL", "VALID_UNCERTAIN", "INVALID_FALSE_MEMORY",
    "INVALID_CONTRADICTION", "INVALID_ATTRIBUTION", "UNDETERMINED",
)
FLAGS = (
    "USED_VALID_MEMORY", "NATURAL_NON_RECALL", "APPROPRIATE_UNCERTAINTY",
    "OMITTED_AVAILABLE_MEMORY", "UNSUPPORTED_ADDITION", "NEGATION_ERROR",
    "CORRECTION_ERROR", "TEMPORAL_ERROR", "PARTICIPANT_ERROR",
)
FIELDS = [
    "turn", "user_input", "llm_response", "relevant_known_facts",
    "relevant_previous_turns", "expected_words", "unexpected_words",
    "primary_class", "secondary_flags", "confidence", "evaluation_reason",
    "diagnosis_needed", "raw_activation_words", "post_score_selection_words",
    "post_fatigue_words", "working_memory_words", "prompt_words", "final_prompt",
    "response_used_expected_words", "response_used_unexpected_words",
    "expected_stage_trace", "drop_reasons", "word_policy_events",
    "backend", "model", "llm_succeeded", "fallback_used",
    "generation_failure_type", "response_time_ms", "evaluator", "evaluated_at",
    "evaluation_version",
]

def js(v: Any) -> str:
    return json.dumps(v if v is not None else [], ensure_ascii=False, sort_keys=True)

def pick(d: Any, *keys: str, default=None):
    if not isinstance(d, dict): return default
    for k in keys:
        if k in d and d[k] is not None: return d[k]
    return default

def load(path: Path):
    rows=[]
    for no,line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(),1):
        if not line.strip(): continue
        try: rows.append(json.loads(line))
        except json.JSONDecodeError as e: raise SystemExit(f"{path}:{no}: invalid JSON: {e}")
    return rows

def as_word_list(value: Any):
    if value is None: return []
    if isinstance(value, list):
        out=[]
        for x in value:
            if isinstance(x,str): out.append(x)
            elif isinstance(x,dict): out.append(str(pick(x,"word","text","surface", default=x)))
            else: out.append(str(x))
        return out
    return [str(value)]

def extract_stage_words(row: dict, stage: str):
    # Research-log schemas have evolved. Prefer explicit stage arrays, then diagnostics.
    for parent_key in ("recall", "diagnostics", "evaluation"):
        parent=row.get(parent_key,{})
        if isinstance(parent,dict):
            for key in (stage, stage+"_words"):
                if key in parent: return as_word_list(parent[key])
    return []

def convert(r: dict):
    ev=r.get("evaluation",{}) or {}
    gen=r.get("response_generation",{}) or {}
    resp=r.get("response",{}) or {}
    wm=r.get("working_memory",{}) or {}
    recall=r.get("recall",{}) or {}
    # Fixture words may live under evaluation in current research logs.
    expected=pick(ev,"expected_words", default=pick(r,"expected_words", default=[]))
    unexpected=pick(ev,"unexpected_words", default=pick(r,"unexpected_words", default=[]))
    final_text=pick(resp,"final_text","text", default=pick(r,"response_text", default=""))
    input_text=pick(r,"input_text","user_input", default="")
    prompt=pick(r,"final_prompt","prompt", default="")
    if isinstance(prompt,dict): prompt=pick(prompt,"text","final_text", default=js(prompt))
    wm_words=as_word_list(pick(wm,"words", default=pick(ev,"working_memory_words", default=[])))
    response_expected=pick(ev,"response_used_expected_words","response_used_expected", default=[])
    response_unexpected=pick(ev,"response_used_unexpected_words","response_used_unexpected", default=[])
    out={k:"" for k in FIELDS}
    out.update({
        "turn": r.get("turn",""), "user_input": input_text, "llm_response": final_text,
        # Gold facts/history are intentionally blank unless explicitly present in the log.
        "relevant_known_facts": js(pick(r,"relevant_known_facts","known_facts", default=[])),
        "relevant_previous_turns": js(pick(r,"relevant_previous_turns", default=[])),
        "expected_words": js(expected), "unexpected_words": js(unexpected),
        "primary_class":"", "secondary_flags":"[]", "confidence":"",
        "evaluation_reason":"", "diagnosis_needed":"",
        "raw_activation_words": js(extract_stage_words(r,"raw_activation")),
        "post_score_selection_words": js(extract_stage_words(r,"post_score_selection")),
        "post_fatigue_words": js(extract_stage_words(r,"post_fatigue")),
        "working_memory_words": js(wm_words),
        "prompt_words": js(pick(r,"prompt_words", default=[])), "final_prompt": prompt,
        "response_used_expected_words": js(response_expected),
        "response_used_unexpected_words": js(response_unexpected),
        "expected_stage_trace": js(pick(ev,"expected_stage_trace", default={})),
        "drop_reasons": js(pick(ev,"dropped_reason_counts","drop_reasons", default={})),
        "word_policy_events": js(pick(ev,"word_policy_events", default=[])),
        "backend": pick(gen,"backend", default=""),
        "model": pick(gen,"model","response_model", default=pick(r,"model", default="")),
        "llm_succeeded": pick(gen,"llm_succeeded", default=""),
        "fallback_used": pick(gen,"fallback_used", default=""),
        "generation_failure_type": pick(gen,"failure_type", default=""),
        "response_time_ms": pick(gen,"elapsed_ms","response_ms", default=""),
        "evaluator":"", "evaluated_at":"", "evaluation_version":"human_valid_v0.1",
    })
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("research_jsonl", type=Path)
    ap.add_argument("-o","--output", type=Path, required=True)
    ap.add_argument("--include-non-llm", action="store_true", help="also export fallback/skipped responses")
    args=ap.parse_args()
    source=load(args.research_jsonl)
    selected=[]
    skipped={}
    for r in source:
        backend=pick(r.get("response_generation",{}),"backend", default="")
        if not args.include_non_llm and backend != "llm":
            skipped[backend]=skipped.get(backend,0)+1; continue
        selected.append(convert(r))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction="raise"); w.writeheader(); w.writerows(selected)
    print(f"[done] input={len(source)} exported={len(selected)} output={args.output}")
    if skipped: print("[excluded] "+", ".join(f"{k or '<empty>'}={v}" for k,v in sorted(skipped.items())))
    print("[human-valid] primary_class is intentionally blank; classify blind from user_input + relevant facts/history + llm_response before diagnosis columns.")
    print("[classes] "+" | ".join(CLASSES))
    print("[flags] "+" | ".join(FLAGS))

if __name__=="__main__": main()
