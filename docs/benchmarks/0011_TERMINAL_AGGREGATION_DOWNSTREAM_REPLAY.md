# Terminal Aggregation Downstream Replay

This phase validates terminal-depth aggregation without changing Production Recall.

The validator starts from Research Logger schema-v2 observations, reconstructs the captured `ActivationResult`, and executes the current `ActivationGate` / ThreadGroup / fatigue / Working-Memory selection twice:

1. baseline physical terminal `word -> thread` contributions,
2. terminal contributions aggregated by identical `(source word, destination thread)` edge.

Every captured terminal contribution remains represented by the arithmetic validator. The experiment does not merge Threads, Connections, or provenance and does not change depth, storage mode, Activation policy, Gate policy, Fatigue, Reinforcement, ThreadGroup selection, Working Memory, or the DB schema.

The replay boundary is the captured Activation observation. Candidate word observations are reused from the captured Activation result; thread base/common scores are reconstructed from captured paths. The purpose is to test whether replacing repeated **terminal-edge arithmetic** changes any downstream discrete selection.

Run against a JSONL Research Logger file:

```powershell
$env:PYTHONPATH="$PWD\src"
python src/terminal_aggregation_replay.py `
  --research-log reports/latest_1000t_llm_phase36_research.jsonl `
  --output-json reports/terminal_aggregation_downstream_1000t.json `
  --report-md reports/terminal_aggregation_downstream_1000t.md
```

A ZIP containing exactly one JSONL file can also be supplied directly to `--research-log`.

The strongest success classification is `TERMINAL_AGGREGATION_DOWNSTREAM_EQUIVALENT`. It requires numeric equivalence within tolerance, preserved terminal provenance accounting, and identical replayed ThreadGroup, Gate-word, suppression, Working-Memory-word, abstention outcome, and topic-reentry results for every replayed turn.

This classification is still an **offline validation result**. It is not permission to modify Production traversal automatically. A Production-compatible prototype and measured latency regression run are separate follow-up phases.
