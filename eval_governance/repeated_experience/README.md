# Repeated Experience Storage Analysis

`repeated-experience-analysis` is a read-only comparison of the clean 100-turn and 1000-turn Research Logger/SQLite artifacts. It groups deterministic thread signatures, audits stored state differences, attributes observed paths, and calculates a first-instance-only topology counterfactual.

```bash
python src/threaded_concept_memory_probe.py repeated-experience-analysis \
  --short-research-log /tmp/scale100/research.jsonl \
  --long-research-log /tmp/scale1000/research.jsonl \
  --short-db /tmp/scale100/baseline.db --long-db /tmp/scale1000/baseline.db \
  --output-json /tmp/repeated-experience.json \
  --report-md /tmp/repeated-experience.md \
  --review-queue /tmp/repeated-experience-review.jsonl
```

The `OFFLINE_TOPOLOGY_COUNTERFACTUAL` is arithmetic, not a Production replay, and makes no recall-quality claim. Exact structural identity does not imply state equivalence. Final snapshots cannot recover original conversation turn numbers or per-repeat deltas; these remain `UNAVAILABLE`/`UNKNOWN`. Assistant-created storage is not presumed to be recall-derived.

No deduplication, merge, pruning, retention, schema, learning, reinforcement, threshold, recall, fatigue, composition, or Working Memory change is made.
