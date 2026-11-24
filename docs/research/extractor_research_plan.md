# Extractor Research Plan

This document is a pre-implementation research plan. It does not describe an implemented local Extractor.

## Scope

### Boundary introduced in Phase 1

- A common Extractor contract is defined in `src/trace_recall/extractors/base.py`.
- The existing LLM Extractor is split into `src/trace_recall/extractors/llm.py`.
- The existing fallback Extractor is split into `src/trace_recall/extractors/fallback.py`.
- `src/trace_recall/extractors/factory.py` creates extractors from CLI configuration.
- `src/trace_recall/extractors/local_rule.py` is only a placeholder for the future deterministic Trace-specific extractor.

### Planned for the next Extractor research phase

- Implement a local-rule candidate.
- Compare Extractors through the same downstream recall pipeline.
- Run PC evaluation first.
- Prepare for future Android device evaluation.

### Not planned for the immediate phase

- Separate this work into another repository.
- Immediately integrate into AIKanojyo itself.
- Decide immediately on Sudachi, MeCab, or any specific morphological analyzer.
- Add a Knowledge Layer.
- Remove the LLM Extractor.
- Change production defaults.

## Proposed Module Boundary

The Phase 1 module boundary is implemented as:

```text
src/
├── threaded_concept_memory_probe.py
└── trace_recall/
    └── extractors/
        ├── __init__.py
        ├── base.py
        ├── llm.py
        ├── fallback.py
        ├── local_rule.py
        └── factory.py
```

The engine now obtains an extractor from the factory and calls `extractor.extract(text)`. Participant Reference Normalization remains outside the extractor boundary.

## Extraction Boundary

The intended boundary is:

```text
Original utterance
→ Extractor
→ Participant Reference Normalizer
→ Thread creation
→ Recall pipeline
```

Participant Reference Normalization should remain outside the Extractor because it depends on speaker origin (`created_by`) and conversation participant roles. The Extractor should produce candidate trace words from the utterance; it should not decide whether `私` means `@user` or `@assistant`. Keeping this boundary separate makes Extractor comparison fair and keeps participant policy testable as a feature-ablation dimension.

## Success Criteria

Thresholds are provisional and should be set after baseline measurement. Candidate success criteria are:

- downstream recall quality degrades only within an acceptable range
- empty extraction is rare
- person names, compounds, dates, and emotion words are not damaged
- bridge words are retained often enough for recall scenarios
- extraction is deterministic
- no additional LLM call is required
- latency and memory footprint are compatible with future Android integration
- DB growth and downstream prompt size remain controlled

## Comparison Method

The comparison should hold Trace Memory, Raw Activation, Recall Selection, Working Memory, Prompt View, and evaluation scenarios fixed where possible. The measured question is not whether a local Extractor exactly matches the LLM Extractor, but whether the recall pipeline still surfaces the expected traces.

## Local Rule Extractor v0 Status

LLM Extractor is the current baseline; fallback remains a diagnostic path. Local Rule Extractor v0 is now an experimental deterministic local candidate: it uses no morphological analyzer, no external API, and is not integrated with Android yet.

## Local Rule v0 Generalization Evaluation

Core Benchmark = development-facing baseline (`eval_extractors/extractor_core_ja.jsonl`). Generalization Benchmark = unseen-expression evaluation (`eval_extractors/extractor_generalization_ja.jsonl`). Local Rule v0 is not adopted yet; generalization results determine the next improvement scope.

The generalization benchmark is for observation, not extractor improvement in the same change. It keeps Local Rule, fallback, and LLM comparison conditions fixed, separates raw extractor output from participant-reference-normalized output, and records category summaries, novel-term retention, and long-token diagnostics so possible overfitting to the core fixture can be reviewed by humans.

## Oracle Replay Evaluator

Oracle Replay is an offline evaluator, not a production selector. It replays saved extractor Oracle details JSONL to compare fixed virtual selection strategies before implementation.

It does not alter Trace storage, Recall, or current extractor behavior. It does not change candidate generation, tokenization, gates, activation, working memory, or local-rule selection.

Its purpose is to estimate selector trade-offs before implementing them: expected-hit gain, word-count growth, unmatched added words, and counterexample risk. AIKanojyo integration remains the practical end goal; the next step after a useful replay result is to implement only the smallest promising extractor strategy and verify it downstream.

Dictionary coverage diagnostics keep DB vocabulary coverage separate from built-in protected patterns, mixed-script spans, dates, URLs, email, and other protected-span sources. If DB-derived protected matches are zero, DB dictionary coverage of zero is correct rather than a replay-adjusted score.

### Candidate Span Generator v2

Candidate Span Generator v2 adds only structurally grounded Mixed Script and safe terminal-boundary candidates. New candidates remain diagnostic-only and are not promoted to production extraction output. Oracle Replay is reused to test generalization before any selector change.

The generator records candidate `source` and `reason` metadata for oracle diagnostics while keeping final words, trace persistence, and recall behavior unchanged.

## Mixed Script Promotion Experiment

Mixed Script promotion is experimental and disabled by default. Enable it only for A/B runs with `--enable-mixed-script-promotion` together with the `local-rule` extractor.

Only structurally generated `mixed-script` candidates may be promoted. Terminal-boundary and general alternate candidates remain diagnostic-only, and baseline reconciliation between extractor evaluation and oracle replay is required before interpreting A/B gains.

## Local Rule Segmentation Fixes (v0.1)

Driven by the expected-word stage survival diagnostic: 24 of 26 `stored` losses in the 100T fixture were surface-boundary errors, not missing extraction.

- Attached particle: a residual segment starting right after a protected span drops one attached particle (`ギター|の練習` -> `練習`, `静か|な音楽` -> `音楽`). Words that merely start with the same kana (`のりこ`) are not affected.
- Script split (additive): chunks are also split at hiragana-to-kanji transitions (`まだ苦手` -> `苦手`, `読むなら窓際` -> `読む`, `窓際`). The original chunk is kept; pieces shorter than two characters are not emitted.
- Bridge compound (additive): a non-hiragana modifier cut off by a bridge word is rejoined (`SF|映画` -> `SF映画`).
- Month-day dates without a year are protected (`7月15日`).

100T local-rule no-response: stored 111 -> 128, prompt 72 -> 83 of 137 expected words; unexpected hits 9 -> 10; Working Memory words 341 -> 364. Extractor generalization expected hits 80 -> 95; core benchmark unchanged (35).

Not fixed: `やけど` (split by the `けど` connective), `おはよう`, `気になる`, tense forms such as `晴れた` for `晴れ`. Single-kanji pieces (`鍋`) are deliberately not emitted to avoid hub words; allowing them gave +2 in the 100T fixture and is left for a separate evaluation.
