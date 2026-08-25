# Path Growth Origin Analysis

This offline command attributes long-horizon path growth to stored thread signatures, connection fanout, and repeated traversal paths. It reads final SQLite snapshots and Research Logger schema-v2 files; it does not prune paths, merge storage, tune scores, or change recall results.

```bash
python src/threaded_concept_memory_probe.py path-growth-analysis \
  --short-research-log /tmp/scale100/research.jsonl --long-research-log /tmp/scale1000/research.jsonl \
  --short-db /tmp/scale100/baseline.db --long-db /tmp/scale1000/baseline.db \
  --output-json /tmp/path-growth.json --report-md /tmp/path-growth.md \
  --review-queue /tmp/path-growth-review.jsonl
```

Exact duplicates use a deterministic signature of sorted canonical word identifiers plus existing `created_by`. Shared-word fanout is reported separately and is **not** treated as duplicate memory. Final DB snapshots cannot reconstruct historical thread/connection totals or distinguish connection-only from reinforcement-only changes; those values remain `UNAVAILABLE`/`UNKNOWN` rather than inferred.
