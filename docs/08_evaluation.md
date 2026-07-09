# Evaluation

The evaluation framework executes reproducible conversation scenarios and measures how traces propagate through the recall pipeline.

Rather than evaluating only the final LLM response, the framework evaluates each stage independently:

```text
Conversation
        ↓
Trace Extraction
        ↓
Raw Activation
        ↓
Recall Selection
        ↓
Working Memory
        ↓
LLM (optional)
        ↓
Evaluation Reports
```

This separation makes the recall process explainable and allows each layer to be benchmarked independently.

---

## Evaluation Outputs

Each evaluation run generates:

- Metrics CSV
- Event JSONL
- Markdown Report

These outputs allow both quantitative analysis and detailed inspection of individual recall events.

---

## Core Metrics

Current evaluation includes:

### Recall Quality

- expected_hit_count
- unexpected_hit_count
- recall_precision_like
- recall_noise_count

### Working Memory

- prompt_thread_group_count
- prompt_word_count
- prompt_tokens_rough
- recall_efficiency

### Conversation Policy

- fatigue_suppressed_count

Additional metrics may be introduced as the evaluation framework evolves.

---

## Long Conversation Benchmarks

The architecture has been evaluated across progressively longer conversations.

| Benchmark | Purpose |
|-----------|---------|
| 100 Turns | Compare storage strategies (Weighted vs Count) |
| 1,000 Turns | Verify long-term stability |
| 3,000 Turns | Verify scalability |
| 10,000 Turns | Verify practical long-term operation |

Each benchmark reused the same evaluation framework while increasing conversational history.

---

## Current Findings

The most important result is **not** a particular precision score.

The important finding is that the recall architecture continues to behave consistently even as conversation history grows.

Across long-term benchmarks:

- Prompt size remained stable.
- Working Memory remained compact.
- ThreadGroup count did not grow uncontrollably.
- Topic Fatigue continued to suppress repetitive conversation.
- Count mode maintained high Recall Precision without prompt explosion.

These observations suggest that the architecture scales with conversation length without requiring proportional prompt growth.

---

## Current Research Focus

Memory storage is no longer the primary research topic.

Current evaluation focuses on:

- Recall Selection quality
- Working Memory construction
- Conversation Policy
- Explainable Recall
- Response-aware Recall Efficiency
- Long-term conversational consistency

Future work will evaluate not only **what was recalled**, but also **how effectively recalled traces contribute to natural conversation**.
