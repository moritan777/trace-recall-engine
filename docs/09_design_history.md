# Design History

This project evolved through repeated disagreement, benchmarking, and revision.

## Early Stage

The first goal was simple memory improvement for AIKanojyo. RAG-style retrieval could retrieve facts, but it did not feel like remembering.

## Shift 1: From Text to Fragments

The question changed from:

> How should we retrieve text?

to:

> What remains after an experience fades?

This led to storing traces instead of reconstructed meaning.

## Shift 2: From Weighted to Count

Weighted edges felt too compressed for repeated lived experiences. Repeated experiences should remain as countable traces rather than being collapsed into one strengthened statement.

The 100T comparison moved Count mode into the current Baseline. Weighted mode remains historical and compatibility context rather than the main research path.

## Shift 3: Long-Scale Count Evaluation

Count mode was then evaluated at 1000T, 3000T, and 10000T. These evaluations showed that Working Memory and prompt size did not grow in proportion to total conversation length in the public stress scenarios.

## Shift 4: ThreadGroup, Gate, and Fatigue

Raw Activation and selection were separated. Activation could remain broad, while Activation Gate and ThreadGroup compression kept Working Memory bounded.

Conversation Fatigue was added because remembering and speaking are different problems: a trace can be recalled without needing to appear repeatedly in conversation.

## Shift 5: Prompt View Experiments

Prompt Views were introduced to compare representations of the same selected Working Memory:

- `threadgroup`
- `recall-state`
- `edge`

Prompt representation affected prompt length and response behavior, but it did not replace recall evaluation. No single Prompt View winner has been selected; `threadgroup` remains the compatibility Baseline.

## Shift 6: Speaker Origin and Participant Reference

The `created_by` field records who produced the utterance that created a trace. It is Speaker Origin metadata, not a score bonus.

Participant Reference Normalization uses `created_by` to map first- and second-person references to `@user` and `@assistant`. This helped two-party scenarios, but `created_by` alone did not resolve all participant ambiguity.

Origin ordering was also tested as prompt display policy. Origin ordering alone did not change candidate availability because it does not alter Raw Activation, scoring, or Gate selection.

## Shift 7: Sensitivity Framework and Research Logger

The sensitivity framework added numeric and categorical experiment dimensions, including Prompt View, Participant Reference, and Origin Order.

The Research Logger added prompt/response records for response-enabled inspection. These logs are useful for research but may contain private conversation content.

## Negative and Incomplete Findings Worth Keeping

- `created_by` alone did not resolve participant ambiguity.
- `origin_order` alone did not change recall candidate availability.
- Prompt representation affected response behavior but did not replace recall evaluation.
- LLM extraction could omit bridge words such as `名前`, which can damage downstream recall even when storage and activation are otherwise working.
- Participant Reference Normalization is not a person-word boost or identity-specific search mechanism.

## Current Milestone: Extractor Research Transition

Trace Recall Engine has moved from initial storage-scale validation to Extractor boundary research.

Current state:

- Count mode adopted as Baseline
- Weighted mode excluded from primary evaluations
- ThreadGroup compression implemented
- Activation Gate implemented
- Conversation Fatigue implemented
- Prompt View comparison implemented as Experimental infrastructure
- Participant Reference Normalization implemented as Experimental infrastructure
- Sensitivity Framework implemented
- Research Logger implemented
- Local deterministic Extractor research Planned, not yet implemented

The next question is whether LLM-dependent Trace Extraction can be replaced with a local deterministic method while preserving downstream recall quality.

## Extractor Evaluation Separation

Conversation evaluation came first because the project needed to verify trace recall behavior end to end. The next research step separates extractor evaluation so LLM and fallback extraction can be compared under identical extraction-boundary scenarios before any activation or conversation effects are introduced.

## Local Rule Extractor v0 Status

LLM Extractor is the current baseline; fallback remains a diagnostic path. Local Rule Extractor v0 is now an experimental deterministic local candidate: it uses no morphological analyzer, no external API, and is not integrated with Android yet.

## Local Rule v0 Generalization Evaluation

Core Benchmark = development-facing baseline (`eval_extractors/extractor_core_ja.jsonl`). Generalization Benchmark = unseen-expression evaluation (`eval_extractors/extractor_generalization_ja.jsonl`). Local Rule v0 is not adopted yet; generalization results determine the next improvement scope.

The generalization benchmark is for observation, not extractor improvement in the same change. It keeps Local Rule, fallback, and LLM comparison conditions fixed, separates raw extractor output from participant-reference-normalized output, and records category summaries, novel-term retention, and long-token diagnostics so possible overfitting to the core fixture can be reviewed by humans.

## Local Rule v1: Japanese Trace Tokenizer

Generalization evaluation showed that Dynamic Trace Dictionary and longest-match protection were working, while many remaining failures were concentrated in cutting useful Trace candidates out of unknown Japanese sentences. The next design step therefore separates token candidate generation from local-rule extraction instead of adding more ad-hoc regexes.

`JapaneseTraceTokenizer` is introduced as an independent component. It preserves Protected Spans, proposes recall-oriented chunks by sentence, connective, and particle-like boundaries, and leaves final word choice to the Local Rule Extractor. This creates a cleaner four-layer development path: Tokenizer → Extractor → Trace → Recall.
