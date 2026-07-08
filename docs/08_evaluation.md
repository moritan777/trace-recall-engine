# Evaluation

The evaluation mode runs fixed conversation files and produces reports.

## Evaluation Flow

```text
Conversation JSONL
↓
Learn turns
↓
Ask turns
↓
Recall / Gate / Working Memory
↓
Metrics CSV / Events JSONL / Markdown Report
```

## Core Metrics

- expected_hit_count
- unexpected_hit_count
- recall_precision_like
- recall_noise_count
- fatigue_suppressed_count
- prompt_tokens_rough
- prompt_thread_group_count
- prompt_word_count
- recall_efficiency

## Current Findings

In 1000-turn evaluation, Count mode remained stable enough to continue research.

The most important result was not perfect precision.

The important result was that the architecture did not collapse under long conversation load.
