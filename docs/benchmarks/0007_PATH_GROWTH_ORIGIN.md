# 0007 — Path Growth Origin Analysis

## Summary

The unchanged local-rule/no-response baseline was compared at 100 and 1000 turns. The analysis separates deterministic repeated thread signatures, shared-word fanout, and repeated traversals. It is diagnostic only.

## Thread and connection growth

| metric | 100-turn | 1000-turn |
|---|---:|---:|
| experience threads | 44 | 857 |
| connections | 169 | 2,938 |
| active threads touched / ask | 14.643 | 285.657 |
| connections traversed / ask | 82.304 | 2,691.224 |
| mean paths / candidate | 2.902 | 28.605 |
| maximum paths / candidate | 18 | 351 |

Exact duplicate signatures increased from 8/44 threads to 692/857 threads; unique signatures increased from 36 to 165, and maximum repetition of one signature rose from 3 to 174. The final snapshots therefore show both new storage and much stronger repeated storage. A common word shared by distinct signatures is not a duplicate.

## Path amplification and concentration

Candidate growth was only 27.5%, while path traversal and same-word multi-thread contribution grew much faster. Candidate redundancy rose from 46.19% to 71.96%, and multi-thread same-word contribution from 32.37% to 73.81%. This indicates that both repeated experiences and concentrated high-fanout traversal contribute; it is not merely growth in final candidate cardinality.

## Historical integrity limits

Existing Research Logger rows support interval path/candidate/latency measurements. Final SQLite snapshots do not contain turn-indexed storage snapshots, so historical thread, connection, and mean-fanout totals are explicitly `UNAVAILABLE`. Connection-only versus reinforcement-only repeated experience is `UNKNOWN` rather than inferred.

## Performance relationship

On the clean replay, processing-time correlations at 1000 turns were: connections traversed `0.960`, generated paths `0.889`, threads touched `0.838`, and unique candidates `0.535`. Connections traversed remained the strongest observed relationship. All correlations set `causal_interpretation: false`.

## Root cause

**MIXED_PATH_GROWTH** — repeated experience signatures and high-fanout path concentration both contribute. Connections per stored thread do not by themselves establish connection multiplication.

## Next recommended step

**repeated experience保存を研究する**

No pruning, merging, threshold tuning, retention change, or Production algorithm change is proposed or implemented.
