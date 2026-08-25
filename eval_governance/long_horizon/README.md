# Long-Horizon Baseline Validation

Use the existing `long_100t_mixed_recall.jsonl` and
`long_1000t_trace_recall_stress_v2.jsonl` fixtures with identical production
baseline options and Research Logger schema v2. `baseline-scale-validation`
then compares both logs and optional SQLite snapshots:

```bash
python src/threaded_concept_memory_probe.py baseline-scale-validation \
  --short-research-log /tmp/scale100/research.jsonl \
  --long-research-log /tmp/scale1000/research.jsonl \
  --short-db /tmp/scale100/baseline.db \
  --long-db /tmp/scale1000/baseline.db \
  --output-json /tmp/baseline-scale.json \
  --report-md /tmp/baseline-scale.md \
  --annotation-template /tmp/baseline-1000-annotation-template.jsonl
```

The optional 20–30-row overlay template is a deterministic review queue. It
uses `MAY_RECALL`, `AMBIGUOUS`, and `REVIEW_REQUIRED`; it does not manufacture
human judgements. Stable Fact responsibility remains separate from associative
metrics. Pseudo-reentry cannot be inferred from schema-v2 observations alone and
is reported as unavailable rather than as a false success.

Metric classification uses the sign of the raw delta with no tolerance
threshold; raw and relative deltas are always retained. Resource growth remains
descriptive and is not an algorithm-tuning trigger. No composition strategy is
connected and no production baseline parameter is changed.
