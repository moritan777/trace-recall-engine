# Future Research

The current architecture has completed its initial storage and long-scale recall validation. Future work now focuses on the extraction boundary and on later integration-quality evaluation.

---

## Completed or Moved Out of Primary Future Scope

The following are no longer primary future items because they have already been evaluated or moved into supporting infrastructure:

- 3000-turn stress test
- 10000-turn stress test
- Count-mode long-scale baseline evaluation
- Activation Gate and ThreadGroup compression for bounded Working Memory
- Conversation Fatigue as an implemented policy layer
- Prompt View comparison infrastructure
- Participant Reference feature-ablation infrastructure
- Research Logger outputs for prompt/response inspection

These results do not make the project finished. They only move the main bottleneck from storage-scale validation to Extractor and integration research.

---

## Current Priority Order

1. Extractor replacement boundary
2. Deterministic local extraction
3. Extractor comparison through downstream recall
4. Android feasibility evaluation
5. AIKanojyo integration design
6. Long-term storage and performance after local extraction
7. Conversation-quality evaluation after integration

---

## 1. Extractor Replacement Boundary

Current trace extraction relies on an LLM when an endpoint is configured. The LLM Extractor remains the Implemented research Baseline, but it adds latency, non-determinism, endpoint dependency, and cost.

The next research phase should define an Extractor contract and compare the current LLM Extractor with the fallback path and planned local alternatives.

---

## 2. Deterministic Local Extraction

A Trace-specific Local Rule Extractor is Planned. Morphological-analysis-assisted extraction is a Candidate, not a selected approach.

The goal is not to match the LLM Extractor word-for-word. The goal is to preserve downstream recall quality while reducing dependence on additional LLM calls.

---

## 3. Downstream Recall Comparison

Extractor candidates should be evaluated through the same recall pipeline and public scenarios where possible.

Important measures include expected hits, unexpected hits, empty extraction rate, compound retention, bridge-word retention, latency, DB growth, and downstream prompt size.

---

## 4. Android Feasibility

AIKanojyo integration requires eventual mobile feasibility. Android evaluation is Future Work and should follow PC-side Extractor comparison.

---

## 5. AIKanojyo Integration Design

Trace Recall Engine is the generalizing recall research base. AIKanojyo is the first intended practical integration target.

Immediate integration into AIKanojyo is not part of the current repository task. Integration design should happen after the Extractor boundary is better understood.

---

## Supporting Research

Prompt View experiments remain useful, but they are supporting research rather than the main line. Current Prompt Views affect prompt representation and response behavior; they do not replace recall evaluation and no single winner has been selected.

---

## Long-Term Vision

The long-term goal is not to reproduce human memory or prove that Trace Recall Engine replaces RAG.

The goal is to explore whether conversational recall can emerge from:

```text
Trace
        ↓
Activation
        ↓
Recall Selection
        ↓
Working Memory
        ↓
LLM
```

rather than relying only on stored document retrieval.

## Extractor Evaluation Before New Extractors

Local Rule, Sudachi, MeCab, and other extractor research should follow the standalone Extractor Evaluation framework first. Only extractors that are understood at this boundary should move into full conversation evaluation.

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
