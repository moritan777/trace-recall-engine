# Missing Experience Identity Metadata Research

`identity-metadata-analysis` traces an unchanged conversation fixture through the eval/learn pipeline into a final SQLite snapshot. It audits which provenance exists upstream, which fields persist, and which occurrence/event distinctions cannot be reconstructed.

```bash
python src/threaded_concept_memory_probe.py identity-metadata-analysis \
  --conversation-file eval_conversations/long_1000t_trace_recall_stress_v2.jsonl \
  --research-log /tmp/scale1000/research.jsonl --db /tmp/scale1000/baseline.db \
  --output-json /tmp/identity-metadata.json --report-md /tmp/identity-metadata.md \
  --review-queue /tmp/identity-metadata-review.jsonl
```

All hypothetical shapes are marked `OFFLINE_METADATA_COUNTERFACTUAL`, `production_schema_change: false`, and `recall_quality_assumption: NONE`. Source-turn mapping uses stored `source_text + created_by` occurrence counts; individual pairing is ambiguous when storage timestamps collide.

Description Identity ≠ Occurrence Identity ≠ Observation Identity ≠ Mutable Repetition State.

No metadata column, event ID, occurrence ID, session ID, source-turn column, migration, deduplication, upsert, merge, connection rewrite, or Production behavior is implemented.
