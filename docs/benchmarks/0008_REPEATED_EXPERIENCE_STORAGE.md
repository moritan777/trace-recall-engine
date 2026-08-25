# 0008 — Repeated Experience Storage Analysis

## Summary

The unchanged clean 100/1000-turn baseline was analyzed using final SQLite snapshots and Research Logger schema-v2 paths. Structural identity, stored-state equivalence, reinforcement state, annotated utility, and topology arithmetic remain separate.

## Repetition distribution and storage contribution

| metric | 100-turn | 1000-turn |
|---|---:|---:|
| total threads | 44 | 857 |
| unique first instances | 36 | 165 |
| exact repeat instances | 8 | 692 |
| exact-repeat storage share | 18.18% | 80.75% |
| exact-repeat connection share | 14.79% | 76.75% |
| exact-repeat generated-path share | 18.47% | 79.29% |

At 1000 turns, four signatures occur 100+ times and account for 658 stored thread instances. Repetition count correlates with generated path count at `0.797`; it correlates with candidate activation score at `0.584`. These correlations are non-causal.

## State equivalence and reinforcement

Among 34 repeated signature groups at 1000 turns, 30 are `STRUCTURALLY_DUPLICATE_BUT_STATE_DIFFERENT` and 4 are `STRUCTURALLY_AND_STATE_EQUIVALENT` across existing comparable fields. All 34 remain `UNKNOWN` for repeat-event reinforcement classification: the final snapshot proves that a new thread exists but cannot attribute word/thread reinforcement deltas to the individual repeat event.

`REPETITION_SIGNAL_MULTIPLICITY` is observed for all 34 repeated groups because repeated structures coexist with word frequency and path multiplicity signals. This is an observation, not a bug classification.

## High-fanout relationship

Repeat instances account for 76.75% of stored connections. Among the highest-fanout words, repeated-instance shares include `した` 74.87%, `カフェ` 91.10%, and `今日` 95.05%. High fanout therefore includes a large repeated-experience component rather than only diverse signatures.

## Recall utility coverage

Annotated expected/unexpected path coverage is 2.74% at 1000 turns. Unknown paths remain unknown and are not labeled wasteful. The available annotation is insufficient to claim that removing repeats preserves recall quality.

## Offline first-instance counterfactual

`OFFLINE_TOPOLOGY_COUNTERFACTUAL` retains 165 threads and 683 connections, arithmetically removing 692 repeat instances and 2,255 links. Estimated repeated-path reduction is 311,325 observed thread-contribution paths. Mean word fanout changes from 33.39 to 7.76. Top-5% signature path share changes from 79.53% to 18.44% under first-instance-only arithmetic.

This is not a Production replay and makes no Recall Precision, availability, or safety claim.

## Integrity limits

Final snapshots do not map each stored thread to its original conversation turn and cannot reconstruct per-repeat changes in reinforcement or connection weight. Assistant origin alone is not treated as recall-derived provenance. No new semantic identity is introduced.

## Root cause

**MIXED_REPETITION_PRESSURE**

Observed factors:

- `STRUCTURAL_DUPLICATE_ACCUMULATION`
- `REPETITION_SIGNAL_MULTIPLICITY`
- `REPEATED_EXPERIENCE_DRIVES_FANOUT`

## Next recommended step

**storage identityを研究する**

No deduplication, merge, pruning, retention, schema, learning, threshold, reinforcement, or Production Recall change was implemented.
