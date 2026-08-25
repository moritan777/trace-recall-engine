# Evaluation

## Conditional composition feature analysis

The offline `composition-feature-analysis` command tests target-blind candidate
pool features against `GROUP_DIVERSITY` recovery and regression. Feature inputs
exclude targets, labels, ranks, scenario IDs, and coverage tags; rank and family
metadata are interpretation-only cross-checks. It scans observed thresholds and
at most two features rather than fitting an ML model.

With 30 in-sample fixtures, results are overfit-prone diagnostics:
`GROUP_DIVERSITY` is not a production improvement, recovery is not necessarily
safe improvement, and an offline separation signal is not production policy.

`composition-validation` applies the Phase 2.9 `generic_ratio` threshold
unchanged to independent fixtures. Frozen-rule metrics are kept separate from a
validation-only exploratory threshold scan, and feature direction/rank-band
stability is reported across both datasets.

## Long-horizon baseline validation

`baseline-scale-validation` compares 100- and 1000-turn Research Logger schema
v2 observations using the same metric implementation. It reports recall
quality, candidate suppression/root stage, frequency-to-admission relationships,
fatigue/re-entry, activation diffusion, database growth, and turn-time
distribution. Every comparable quality metric retains raw and relative deltas;
the `STABLE`/`IMPROVED`/`DEGRADED` label is a zero-tolerance sign description,
not a newly tuned threshold.

The evaluation framework executes reproducible conversation scenarios and measures how traces propagate through the recall pipeline.

Rather than evaluating only the final LLM response, the framework can evaluate each stage independently:

```text
Conversation
        ↓
Trace Extraction
        ↓
Participant Reference Normalization
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

## Evaluation Modes

### Recall-only evaluation

`eval --no-response` measures extraction, activation, Recall Selection, Working Memory construction, prompt size, expected hits, unexpected hits, and fatigue without generating an LLM response.

### Response-enabled evaluation

When response generation is enabled, the same recall pipeline is used and an LLM response is generated after prompt construction. This mode is useful for inspecting whether prompt representation changes affect response behavior, but it is not a replacement for recall metrics.

### Parameter sensitivity

The `sensitivity` command sweeps numeric and categorical dimensions. Supported dimensions include `gate_max_threads`, `gate_max_words`, `common_bonus`, `prompt_view`, `participant_reference`, and `origin_order`.

Sensitivity response generation is disabled by default. Use `--enable-response-generation` only when LLM responses are part of the experiment.

### Representation comparison

Prompt View experiments compare how the same bounded Working Memory is represented to the LLM.

### Feature ablation

Participant Reference and Origin Order can be disabled or varied for controlled experiments.

### Research logging

The Research Logger can write JSONL and per-turn Markdown records containing prompts, responses, recalled traces, and configuration metadata. These logs may contain private conversation content.

---

## Evaluation Outputs

Each evaluation run generates:

- Metrics CSV
- Event JSONL
- Markdown Report

Optional research logs can also be generated with `--research-log-jsonl`, `--research-log-dir`, or sensitivity `--save-research-log`.

---

## Core Metrics

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

## Prompt View Positioning

Implemented Prompt Views are:

```text
threadgroup
recall-state
edge
```

These are not different Recall algorithms. They are different ways to express the same selected Working Memory in the prompt.

Current experiments show that `recall-state` and `edge` can shorten prompts, and response-enabled evaluation has shown small response differences. A single winner has not been selected. `threadgroup` remains the compatibility Baseline.

Do not treat a single turn or one response-enabled run as proof that one Prompt View is generally best.

---

## Participant Reference Positioning

Participant Reference Normalization uses the speaker origin recorded as `created_by` to normalize first- and second-person references:

```text
created_by
→ pronoun normalization
→ @user / @assistant
```

This is Experimental. It helps distinguish user-origin and assistant-origin participant references, but it does not fully solve person ambiguity.

The current implementation does not add:

- person-word score boosts
- identity-specific search
- `created_by` score bonuses

---

## Origin Order Positioning

`--origin-order` changes prompt display ordering only. It does not change Recall scores, Raw Activation, Activation Gate selection, or candidate availability.

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

The most important result is not a particular precision score. The important finding is that the recall architecture continued to behave consistently in the public long-history benchmarks.

Across long-term benchmarks:

- Prompt size remained stable.
- Working Memory remained compact.
- ThreadGroup count did not grow uncontrollably.
- Conversation Fatigue continued to suppress repetitive conversation.
- Count mode maintained high Recall Precision without prompt explosion.

These observations suggest that the architecture scales with conversation length without requiring proportional prompt growth in the evaluated scenarios.

---

## Current Research Focus

Memory storage is no longer the primary research topic.

Current evaluation now needs to support the extractor transition:

- downstream recall quality after Extractor replacement
- Working Memory construction
- Conversation Policy
- Explainable Recall
- Response-aware Recall Efficiency
- Long-term conversational consistency

Future work will evaluate not only what was recalled, but also how effectively recalled traces contribute to natural conversation.

Benchmark history

↓

Benchmarks

Research progress

↓

Zenn

## Recall governance labels

Evaluation fixtures may annotate a trace target with `SHOULD_RECALL`, `MAY_RECALL`, `SHOULD_NOT_RECALL`, or `MUST_NOT_SPEAK`. The last value is an evaluation label: it does not add privacy, relationship, or boundary semantics to this engine. `MAY_RECALL` never fails solely because it is absent. A candidate-free result and a result where every candidate is suppressed are separately represented as `NO_CANDIDATES` and `CANDIDATES_SUPPRESSED`; both are valid outcomes.

The offline `trace_recall.offline` lateral-inhibition experiment reports expected-hit gain/loss, unexpected-hit reduction, selected size, prompt-size impact, and counterexamples. It is not called by the production gate or selector.
