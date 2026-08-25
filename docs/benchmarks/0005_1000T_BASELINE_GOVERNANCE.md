# Benchmark 005 — 100 vs 1000 Production Baseline

Both existing fixtures were run with the local-rule extractor, response
generation disabled, and otherwise unchanged production defaults. Research
Logger schema v2 and independent SQLite databases were captured. The 100-turn
fixture produced 56 ask observations; the 1000-turn fixture produced 143.

| Metric | 100 | 1000 | Relative delta |
|---|---:|---:|---:|
| Recall precision | 0.889881 | 0.855478 | -3.87% |
| Unexpected recall / ask | 0.160714 | 0.202797 | +26.18% |
| Abstention rate | 0.035714 | 0.097902 | +174.13% |
| Activation candidates / ask | 12.357143 | 15.755245 | +27.50% |
| Candidate suppressions / ask | 6.267857 | 11.209790 | +78.85% |
| Prompt tokens / ask | 568.232143 | 542.188811 | -4.58% |
| Working-Memory words / ask | 6.089286 | 4.545455 | -25.35% |
| Competition density | 2.429165 | 4.112784 | +69.31% |
| Average processing ms / ask | 14.737799 | 180.110617 | +1122.10% |
| p95 processing ms | 27.697034 | 494.309386 | +1684.70% |

Scale grew from 44 to 857 experience threads, 169 to 2,938 connections,
200,704 to 970,752 DB bytes, while unique word nodes remained 88. Fatigue was
observed 86 times across 15 topics; 71 were repeated suppressions. Explicit
re-entry recovered on all 106 observed re-entry turns. Pseudo-reentry is not
derivable from the captured schema and is reported as unavailable.

Activation diffusion increased while prompt and Working-Memory sizes remained
bounded. The baseline therefore receives
`SCALE_DEGRADATION_NEEDS_RESEARCH`; the next recommendation is to research only
the most degraded subsystem. This report does not tune or replace any algorithm.
