# Experience Thread Storage Identity Analysis

`storage-identity-analysis` compares five offline identity levels against unchanged 100/1000-turn SQLite snapshots and Research Logger records. It emits JSON, Markdown, and a human review queue.

```bash
python src/threaded_concept_memory_probe.py storage-identity-analysis \
  --short-research-log /tmp/scale100/research.jsonl \
  --long-research-log /tmp/scale1000/research.jsonl \
  --short-db /tmp/scale100/baseline.db --long-db /tmp/scale1000/baseline.db \
  --output-json /tmp/storage-identity.json --report-md /tmp/storage-identity.md \
  --review-queue /tmp/storage-identity-review.jsonl
```

All model sizes carry `OFFLINE_IDENTITY_COUNTERFACTUAL`, `production_replay: false`, and `recall_quality_assumption: NONE`. Timestamps are storage observations, not proven event identity. Expected annotations affect only the separately reported utility overlay and never identity grouping.

- Same word set ≠ same Experience.
- Same Experience ≠ same state.
- Repeating an Experience ≠ proof that multiple Experiences exist.

No identity key, semantic hash, deduplication, upsert, merge, schema, learning, Recall, reinforcement, connection, or Working Memory behavior is implemented or changed.
