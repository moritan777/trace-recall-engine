# Trace Recall Engine Benchmarks

This directory contains benchmark reports for the Trace Recall Engine.

The purpose of these benchmarks is not to evaluate final LLM response quality.
The purpose is to evaluate whether trace-based recall can scale while keeping Working Memory bounded.

## Purpose

Keep a research-log index of benchmark results and design decisions for trace-based recall scalability.

## Configuration

Reports in this directory summarize Markdown benchmark outputs only. CSV and JSONL artifacts are intentionally out of scope for this documentation pass unless noted by a source report.

## Benchmark Index

| ID | Scenario | Mode | Purpose |
|---|---|---|---|
| [001](001_100T_weighted_vs_count.md) | 100T Weighted vs Count | response enabled | Compare storage strategies |
| [002](002_1000T_count.md) | 1000T Count | no-response | Validate long-term recall stability |
| [003](003_3000T_count.md) | 3000T Count | no-response | Validate scalability |
| [004](004_10000T_count.md) | 10000T Count | no-response | Validate practical-scale stability |

## Results

The benchmark sequence records the transition from storage-strategy comparison to large-scale Count-mode stability checks at 1000T, 3000T, and 10000T.

## Findings

## Key Findings

- Count-based Thread accumulation was adopted over Weighted Thread Strength.
- ThreadGroup compression prevents prompt explosion.
- Activation Gate separates raw activation from Working Memory.
- Conversation Fatigue separates recall strength from conversation exposure.
- 10000T evaluation confirmed that prompt size scales with Working Memory size, not with total conversation length.

## Interpretation

The benchmark history should be read as evidence that the primary research bottleneck moved away from memory storage and toward selection and policy layers.

## Current Research Focus

The research focus has shifted from memory storage to:

1. Recall Selection
2. Working Memory Policy
3. Conversation Policy

## Conclusion

Trace Recall Engine benchmark documentation now treats Count-mode storage as the baseline and Weighted mode as excluded from future primary evaluations.
