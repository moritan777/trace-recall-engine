# AIKanojyo Memory Engine Bible

## Status legend

- **Verified**: confirmed in the current repository code, tests, or generated reports.
- **Experimental**: implemented for research or A/B measurement, but not accepted as an AIKanojyo default.
- **Planned**: recommended future AIKanojyo work, not implemented in this Python probe.
- **Not Implemented**: explicitly absent from this repository.
- **Rejected**: considered and not adopted for the current handover path.
- **Paused**: research is intentionally stopped until AIKanojyo-level evidence requires reopening it.

## 1. Purpose of this document

This document is the permanent design and decision record for handing the Trace Memory Engine research in this repository to AIKanojyo developers. The repository is a Python research probe for AIKanojyo's future memory architecture, not the AIKanojyo production application itself.

Read this first if you are an AIKanojyo implementer, a future Codex session, a future ChatGPT chat, the original developer returning later, or an external technical reviewer. Update this Bible when a major design decision changes. Do not silently delete old rationale; append design history and mark superseded points clearly.

## 2. Final purpose of the project

```text
このリポジトリの目的は、完璧な日本語TokenizerやExtractorを作ることではない。

AIKanojyoのMemory Engineを支えるTrace抽出・保存・Recall・Working Memory・Prompt構築を検証し、実運用に耐える最小構成を見つけることである。

Extractorは目的ではなく手段である。
```

The practical goal is to find the smallest deterministic Trace pipeline that can support relationship-like recall in AIKanojyo without making memory feel like document search.

## 3. Trace Memory principle

```text
Conversation
↓
Extractor
↓
Word
↓
Thread
↓
Connection
↓
Activation
↓
Gate
↓
Working Memory
↓
Prompt
↓
LLM
```

Core principles:

- Do **not** freeze the full meaning of the original text as the stored memory unit.
- Store small **Word / Thread / Connection** traces.
- Reconstruct meaning at Recall time through activation, gate selection, Working Memory, and prompt construction.
- Do not split “knowledge” and “memory” into unrelated systems at this layer; both can be represented as traces when they participate in recall.
- Preserve speaker direction separately: `created_by` records who produced the utterance, while Participant Reference Normalization can add canonical role traces such as `@user` and `@assistant`.

## 4. Research history

| Stage | Problem | Findings | Current status |
|---|---|---|---|
| LLM Extractor | Quickly produce Trace words while the recall architecture was still changing. | Useful research baseline, but depends on an endpoint, cost, latency, and nondeterminism. | **Verified / Baseline**, not the production target. |
| Fallback Extractor | Keep diagnostics and basic operation possible without an LLM endpoint. | Deterministic and simple, but not sufficient as the selected production extractor. | **Verified / Diagnostic fallback**. |
| Local Rule Extractor | Test a deterministic local candidate without morphological analyzers. | Preserves many trace cues in core scenarios and is portable in principle. Generalization and holdout are weaker. | **Experimental adoption candidate**. |
| Extractor Boundary separation | Compare extractors without changing storage, activation, gate, or prompt logic. | `TraceExtractor.extract(text)` makes extractor replacement testable. | **Verified / Adopted**. |
| Participant Reference Normalization | Preserve user/assistant direction without putting speaker policy in extraction. | `created_by`-aware normalization adds role traces after extraction. | **Verified / Adopted boundary**, incomplete coverage. |
| Dynamic Trace Dictionary | Reuse existing Trace DB vocabulary to protect known words. | Avoids maintaining a separate dictionary DB; longest-match diagnostics are available. | **Verified / Adopted candidate**. |
| Japanese Trace Tokenizer | Generate recall-oriented Japanese surface chunks without a full tokenizer. | Useful as a Trace-specific tokenizer, not a morphological analyzer. | **Verified / Experimental component**. |
| Candidate Span Generator | Measure mixed-script and terminal-boundary candidates without changing final output. | Adds `source` and `reason` metadata for oracle diagnostics. | **Verified / Diagnostic**, with limited mixed-script promotion experiment. |
| Oracle Evaluation | Separate generated candidates from final selected words. | Shows selection loss vs tokenizer loss. | **Verified / Research-only**. |
| Generalization Benchmark | Detect overfitting to core Japanese scenarios. | Local-rule drops materially outside core. | **Verified / Research-only benchmark**. |
| Oracle Replay | Estimate selector strategies before implementing them. | Broad candidate promotion can improve hits but adds many unmatched words. | **Verified / Research-only**. |
| Mixed Script Candidate | Preserve terms such as product names written with mixed scripts. | Candidate generation has coverage; final extraction does not promote by default. | **Verified / Diagnostic**. |
| Experimental Mixed Script Promotion | Test a bounded production-like selector change. | Improves generalization mixed-script final coverage in an A/B report, but dataset-level adoption is not proven. | **Experimental / default OFF**. |

## 5. Current architecture verified in code

Primary implementation files:

- `src/threaded_concept_memory_probe.py`: storage, activation, gate, prompt views, CLI, evaluation commands, participant normalization, and research logging utilities.
- `src/trace_recall/extractors/base.py`: `ExtractedWord`, `ExtractionResult`, `TraceExtractor`, normalization and dedupe helpers.
- `src/trace_recall/extractors/llm.py`: `LLMTraceExtractor`.
- `src/trace_recall/extractors/fallback.py`: `FallbackTraceExtractor` and fallback extraction path.
- `src/trace_recall/extractors/local_rule.py`: `LocalRuleTraceExtractor`, protected spans, trace dictionary integration, mixed-script promotion flag.
- `src/trace_recall/extractors/japanese_trace_tokenizer.py`: `JapaneseTraceTokenizer` and tokenizer diagnostics.
- `src/trace_recall/extractors/candidate_span_generator.py`: `CandidateSpan`, `CandidateSpanGenerator` for v2 diagnostic candidates.
- `src/trace_recall/extractors/factory.py`: extractor creation.

Verified classes and functions include:

- Extractor interface: `TraceExtractor.extract(text) -> list[ExtractedWord]`.
- Storage: `ThreadedConceptMemoryStore`, `WordNode`, `Thread`, `WordThreadLink`, SQLite tables `words`, `threads`, `word_threads`, and `conversation_exposures`.
- Dynamic Trace Dictionary: `ThreadedConceptMemoryStore.get_trace_vocabulary()` and `TraceVocabularyProvider`.
- Participant Reference Normalizer: `normalize_participant_references(...)`.
- Activation / Recall: `ActivationEngine`, `ActivationTrace`, `ActivationResult`.
- Gate: `ActivationGate`, `GatedWord`, `GatedThread`, `GatedThreadGroup`, `GatedContext`.
- Prompt views: `format_gated_recall_context`, `format_threadgroup_view`, `format_recall_state_view`, `format_edge_view`, `build_response_prompt`.
- Research and evaluation components: `cmd_eval`, `cmd_sensitivity`, `cmd_eval_extractor`, `cmd_oracle_replay`, `evaluate_extractor_scenario`, `evaluate_oracle_replay_row`.

## 6. Adopted design decisions

### Why the LLM Extractor is not the production premise

- External dependency and API/network failure modes.
- Runtime cost and latency.
- Non-deterministic output complicates regression testing.
- Poor fit for Android/offline portability.

### Why Local Rule is the current adoption candidate

- Deterministic and fast.
- No third-party dependency and no external API.
- C# port is realistic because the rules are regex/string based.
- Trace Memory does not require perfect morphological parsing; it requires enough stable cues for downstream recall.

### Why Tokenizer and Extractor are separated

`JapaneseTraceTokenizer` proposes primary and alternate chunks. `LocalRuleTraceExtractor` selects and weights final Trace words. This makes tokenizer loss, selector loss, and final extraction behavior measurable separately.

### Why Participant Reference is outside the Extractor

`私`, `あなた`, and similar references depend on `created_by` and participant roles. The extractor only sees text; role normalization belongs after extraction so extractor comparison remains fair and role policy remains testable.

### Why Trace DB vocabulary is reused as a dictionary

The Trace Store already knows words that mattered in previous conversations. Reusing it as protected-span vocabulary avoids a separate hand-maintained dictionary DB and lets AIKanojyo preserve user-specific names and terms discovered through use.

### Why Oracle / Replay should not be ported to production

Oracle labels, expected words, replay strategies, CSV/Markdown generation, and benchmark fixtures are measurement tools. Porting them into AIKanojyo would mix research ground truth with runtime memory behavior and create unnecessary app complexity.

## 7. Rejected or paused alternatives

| Alternative | Status | Reason |
|---|---|---|
| Sudachi | **Paused / not selected** | Strong tokenizer, but adds dependency, packaging, dictionary, and Android/C# port questions beyond the minimal Trace goal. |
| MeCab | **Paused / not selected** | Similar dependency and native integration burden; full morphology is not required for Trace cue retention. |
| Janome | **Paused / not selected** | Pure Python helps the probe but does not solve C#/Android integration and is still heavier than local rules. |
| Always-on LLM Extractor | **Rejected for production premise** | Cost, nondeterminism, latency, external dependency, and portability concerns. |
| Embedding-based word boundary generation | **Rejected for this phase** | Reintroduces vector/model dependence at the boundary where deterministic portability is desired. |
| TextRank | **Paused** | Ranks salient terms but does not solve participant direction, trace continuity, or Japanese boundary reliability for this use case. |
| Learning to Rank | **Paused** | Needs labeled data and training/evaluation infrastructure not justified before AIKanojyo shadow evidence. |
| Logistic regression | **Paused** | Same labeled-data burden; premature before the integration path proves value. |
| Promote all alternate spans | **Rejected** | Oracle Replay shows broad additions can improve hits but add many unmatched words. |
| Terminal Boundary production promotion | **Rejected / diagnostic only** | Candidate source is noisy and remains useful for diagnosis rather than runtime output. |
| Category-specific selector | **Paused** | Adds benchmark-specific complexity and risk of overfitting before real AIKanojyo logs. |
| Candidate classifier | **Paused** | Requires labels and introduces model lifecycle complexity. |
| Individual person-name dictionary | **Rejected as static strategy** | User-specific names should come from Trace DB vocabulary, not from hard-coded person dictionaries. |
| Product-name dictionary | **Rejected as static strategy** | Mixed-script structural candidates are preferred over endless product dictionaries. |

## 8. Evaluation results verified on current code

These values were generated from the current branch with temporary reports on 2026-07-14 UTC. They are benchmark measurements for fixed fixtures, not claims of general Japanese tokenizer accuracy.

### Core Benchmark (`eval_extractors/extractor_core_ja.jsonl`, `local-rule`)

- Scenario count: 14.
- Expected hit: 35; missing: 2.
- Oracle coverage: 35/37 (94.6%).
- Final coverage: 35; selection loss: 0; tokenizer loss: 2.
- Bridge: 12/12; compound: 6/6; identity: 5/6.

### Generalization Benchmark (`eval_extractors/extractor_generalization_ja.jsonl`, `local-rule`)

- Scenario count: 63.
- Expected hit: 80; missing: 66.
- Oracle coverage: 101/123 (82.1%).
- Final coverage: 71; selection loss: 30; tokenizer loss: 22.
- Bridge: 24/35; compound: 7/13; novel-term exact retention: 5/17 (29.4%).

### Mixed Script Promotion A/B (`local-rule --enable-mixed-script-promotion` on Generalization)

- Expected hit improves from 80 to 88.
- Missing decreases from 66 to 58.
- Final coverage improves from 71 to 79.
- Mixed-script final coverage improves from 0.0% to 71.4%.
- This remains **Experimental** and default OFF; it is not a dataset-level production decision.

### Holdout (`eval_extractors/oracle_replay_holdout_ja.jsonl`, `local-rule`)

- Scenario count: 90.
- Expected hit: 35; missing: 67.
- Oracle coverage: 59/102 (57.8%).
- Final coverage: 35; selection loss: 24; tokenizer loss: 43.
- Novel-term exact retention: 2/28 (7.1%); identity: 17/25.

### Oracle Replay and baseline reconciliation

- Oracle Replay is offline advisory only.
- `current-final` remains the baseline: core 35 hits, generalization 80 hits, holdout 35 hits.
- Broad strategies such as `final-plus-all-candidates` improve generalization and holdout hits but add many unmatched candidates.
- Bounded strategies improve some datasets but still increase word growth and unmatched words.
- Therefore replay does not justify promoting all candidates into production.

### Human integration interpretation

“AIKanojyo用途で80〜85%” is not a formal benchmark value in this repository. Treat it only as a human, integration-level judgment that the Local Rule path may be good enough to test inside AIKanojyo as an Experimental / Shadow path. Correct interpretation: Core shows high retention, Generalization drops, and Holdout exposes clear limitations. Trace Memory should now be evaluated by end-to-end recall and prompt behavior rather than by chasing perfect Japanese segmentation.

## 9. Current conclusion

- Extractor research is **Paused** at the repository level.
- Do not aim for perfect Japanese segmentation before integration.
- The next evidence should come from AIKanojyo-level evaluation: storage, recall, gate, Working Memory, prompt behavior, and real conversation logs.
- Return to extractor research only if real conversations show severe trace loss that downstream recall cannot recover.
- Mixed Script Promotion is **Experimental** and default OFF.
- Terminal Boundary candidates are diagnostic only.

## 10. Update rules

When a major design decision changes:

1. Add a dated note or a new subsection.
2. Preserve the previous rationale as Design History unless it is factually wrong.
3. Mark status using Verified / Experimental / Planned / Not Implemented / Rejected / Paused.
4. Link to code, reports, or AIKanojyo evidence that justified the change.
