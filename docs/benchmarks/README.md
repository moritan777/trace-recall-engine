# Trace Recall Engine Benchmarks

This directory contains public benchmark reports for the Trace Recall Engine.

The purpose of these benchmarks is not to evaluate final LLM response quality. The purpose is to evaluate whether trace-based recall can scale while keeping Working Memory bounded.

## Scope

These benchmarks primarily evaluate recall behavior, Working Memory size, prompt size, and scalability.

They do not establish final conversational quality and do not prove superiority over other memory systems.

CSV, JSONL, SQLite databases, and sensitivity outputs are local generated artifacts unless explicitly committed.

## Benchmark Index

| ID | Scenario | Mode | Report |
|---|---|---|---|
| 001 | 100T Weighted vs Count | response enabled | [100T summary](0001_100T.md), [Weighted](0001_long100_weighted.md), [Count](0001_long100_count.md) |
| 002 | 1000T Count | no-response | [1000T summary](0002_1000T.md), [Count details](0002_long1000_count.md) |
| 003 | 3000T Count | no-response | [3000T summary](0003_3000T.md), [Count details](0003_long3000_count.md) |
| 004 | 10000T Count | no-response | [10000T summary](0004_10000T.md), [Count details](0004_long10000_count.md) |

## Four-Stage Research Story

| Scale | Research Question | Main Result |
|---:|---|---|
| 100T | Weighted or Count? | Count was selected as the current Baseline. |
| 1,000T | Does Count remain usable at longer scale? | Long-term Count behavior remained usable in the public stress scenario. |
| 3,000T | Does the pipeline scale further? | Working Memory and prompt size remained bounded in the stress scenario. |
| 10,000T | Does practical-scale use collapse? | Prompt size did not grow with total history; the 10,000T summary reports Recall Precision 0.927, average prompt size 429 tokens, average ThreadGroups 1.78, and 764 fatigue suppressions. |

## Key Findings

- Count-based Thread accumulation was adopted over Weighted Thread Strength for the current Baseline.
- ThreadGroup compression prevents repeated experiences from expanding prompts directly.
- Activation Gate separates broad Raw Activation from bounded Working Memory selection.
- Conversation Fatigue separates recall strength from repeated prompt exposure.
- 10000T evaluation confirmed that prompt size scales with Working Memory size, not with total conversation length, in the public stress scenario.

## Interpretation

The benchmark history should be read as evidence that the primary research bottleneck moved away from memory storage and toward selection, policy, and extraction-boundary research.

## Next Benchmark Phase

The next benchmark phase focuses on extractor replacement. See the [Current Research Direction](../research/current_research_direction.md) and [Extractor Research Plan](../research/extractor_research_plan.md).

## Related History

- [Benchmark History](benchmark_history.md)
- [Research Log](Research_Log.md)
