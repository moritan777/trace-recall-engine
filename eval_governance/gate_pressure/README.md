# Activation Gate Pressure Analysis

`gate-pressure-analysis` consumes the same 100- and 1000-turn Research Logger
schema-v2 files used by long-horizon validation:

```bash
python src/threaded_concept_memory_probe.py gate-pressure-analysis \
  --short-research-log /tmp/scale100/research.jsonl \
  --long-research-log /tmp/scale1000/research.jsonl \
  --output-json /tmp/gate-pressure.json \
  --report-md /tmp/gate-pressure.md \
  --review-queue /tmp/gate-pressure-review.jsonl
```

The analysis uses only captured candidate, path, thread, score, frequency,
diagnostic, evaluation, and timing metadata. Ambiguous Gate reasons remain
`UNCLASSIFIED`; no semantic suppression cause is invented. Gate/suppression
efficiency includes explicit annotation coverage.

Schema v2 exposes recall and total timing but not DB lookup, traversal, Gate,
selection, Working-Memory, or logging substage timers. Those stages are reported
as unavailable instead of estimated. The analyzer is read-only, so runtime
output equivalence is preserved without adding timers to production.

The review queue is capped at 25 and retains `MAY_RECALL`, `AMBIGUOUS`, and
`REVIEW_REQUIRED`. No threshold, algorithm, strategy, extractor, fatigue,
reinforcement, connection, or Working-Memory policy is modified.
