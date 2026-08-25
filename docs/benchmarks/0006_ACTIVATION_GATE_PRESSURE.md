# Benchmark 006 — Activation Gate Pressure

The unchanged 100- and 1000-turn local-rule/no-response baseline logs from
Benchmark 005 were decomposed offline.

| Metric | 100 | 1000 | Change |
|---|---:|---:|---:|
| Candidates / ask | 12.357 | 15.755 | +27.5% |
| Gate selection rate | 49.28% | 28.85% | -20.43 points |
| Active threads / ask | 14.643 | 285.657 | +1850.8% |
| Traversed connections / ask | 82.304 | 2,691.224 | +3169.9% |
| Paths / candidate | 2.902 | 28.605 | +885.8% |
| Duplicate-path ratio | 86.71% | 96.27% | +9.57 points |
| Multi-thread same-word ratio | 32.37% | 73.81% | +41.44 points |
| Candidate redundancy ratio | 46.19% | 71.96% | +25.77 points |

At 1000 turns, 1,603 of 2,253 candidates were suppressed. Existing reasons
identify 92 fatigue-related and 49 score-insufficient cases; 1,462 remain
`UNCLASSIFIED` rather than receiving inferred semantics. Depth-2 propagation
accounts for 1,917 candidates and 1,496 suppressions.

Connection traversals correlate with processing time at 0.973; candidate count
correlates at 0.517. These are observational correlations, not causal claims.
Recall timing grew to 190.5 ms average / 553.2 ms p95. Finer stage timings are
not present in schema v2 and were not estimated.

Path, frequency, redundancy, and declining Gate selection all increased, so the
root classification is `MIXED_PRESSURE`. The single next recommendation is to
study path growth. No pruning, tuning, or production change is included.
