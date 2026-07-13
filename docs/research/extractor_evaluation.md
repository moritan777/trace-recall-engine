# Extractor Evaluation

Extractor Evaluation is a standalone benchmark layer for comparing trace-word extractors before their output is used by activation, gating, Working Memory, prompt construction, or conversation evaluation.

## Purpose

The purpose is fairness: the existing `llm` extractor and `fallback` extractor can be run against the same JSONL scenarios and scored with the same metrics. Future Local Rule, Morphological, Sudachi, and MeCab extractors should plug into this boundary without rewriting the evaluation code.

This framework does not improve extraction algorithms, prompts, activation, gates, Working Memory, participant-reference rules, thread generation, weights, sensitivity, the Research Logger, or conversation evaluation.

## Scenario Dataset

The default dataset is `eval_extractors/extractor_core_ja.jsonl`. Each line contains one extraction-boundary sentence and optional expected groups:

- `scenario`
- `category`
- `role`
- `input`
- `expected_words`
- `forbidden_words`
- `bridge_words`
- `compound_words`
- `identity_words`
- `participant_words`

Categories include Identity, Preference, Date, Emotion, Future Plan, Compound Word, Correction, Negation, Third Person, Relationship, Conversation Bridge, and Participant Reference.

## Metrics

The CLI records expected hits, unexpected hits, missing expected words, precision-like and recall-like ratios, bridge hits, identity hits, compound hits, participant hits, empty extraction, word count, average weight, and elapsed milliseconds.

## Bridge Words

Bridge words are trace connection points rather than people or semantic interpretations. Examples include `名前`, `好き`, `誕生日`, `昨日`, `今度`, and `約束`. Bridge hit rate asks whether the extractor preserved words that later recall can use to cross into another trace.

## Compound Words

Compound evaluation checks whether extraction preserves words such as `チーズケーキ`, `見に行く`, `来週`, and `金曜日` as usable trace triggers.

## Identity and Participant Reference

Identity metrics check identity-bearing words such as names and `名前`. Participant metrics check canonical references such as `@user` and `@assistant` when a scenario declares them.

## Difference from Conversation Evaluation

Conversation evaluation starts after memories have been extracted, stored, activated, gated, placed into Working Memory, and optionally used in a response. Extractor evaluation is earlier and narrower: it measures only extraction output at the extraction boundary.

The intended research order is:

```text
Extraction Boundary
↓
Extractor Evaluation
↓
Conversation Evaluation
```

## Getting Started

Run the fallback extractor:

```bash
python src/threaded_concept_memory_probe.py eval-extractor \
  --extractor fallback \
  --scenario eval_extractors/extractor_core_ja.jsonl \
  --metrics-csv reports/extractor_fallback.csv \
  --details-jsonl reports/extractor_fallback.jsonl \
  --report-md reports/extractor_fallback.md
```

Run the LLM extractor with the same scenarios:

```bash
python src/threaded_concept_memory_probe.py eval-extractor \
  --extractor llm \
  --scenario eval_extractors/extractor_core_ja.jsonl \
  --base-url http://127.0.0.1:8080 \
  --model local-model \
  --metrics-csv reports/extractor_llm.csv \
  --details-jsonl reports/extractor_llm.jsonl \
  --report-md reports/extractor_llm.md
```

## Future Research

After this evaluation infrastructure is stable, research can move to Local Rule, Sudachi, MeCab, and other extractor implementations. Those implementations should be compared here before being evaluated in full conversation benchmarks.

## Local Rule Extractor v0 Status

LLM Extractor is the current baseline; fallback remains a diagnostic path. Local Rule Extractor v0 is now an experimental deterministic local candidate: it uses no morphological analyzer, no external API, and is not integrated with Android yet.

## Local Rule v0 Generalization Evaluation

Core Benchmark = development-facing baseline (`eval_extractors/extractor_core_ja.jsonl`). Generalization Benchmark = unseen-expression evaluation (`eval_extractors/extractor_generalization_ja.jsonl`). Local Rule v0 is not adopted yet; generalization results determine the next improvement scope.

The generalization benchmark is for observation, not extractor improvement in the same change. It keeps Local Rule, fallback, and LLM comparison conditions fixed, separates raw extractor output from participant-reference-normalized output, and records category summaries, novel-term retention, and long-token diagnostics so possible overfitting to the core fixture can be reviewed by humans.
