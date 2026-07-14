# AIKanojyo Integration Guide

## 1. Integration purpose

Do not port the Python probe as-is. Introduce the Trace Memory Engine into AIKanojyo as an **Experimental** path that coexists with the current AIKanojyo memory system. The first goal is evidence, not replacement.

Recommended initial shape:

```text
Memory Engine
├── Existing AIKanojyo Memory Path
└── Experimental Trace Memory Path
```

## 2. Porting scope

### Port candidates

- **Local Rule Extractor**: `LocalRuleTraceExtractor`, excluding benchmark-only diagnostics that are not needed at runtime.
- **Surface normalization**: NFKC normalization and whitespace cleanup.
- **Japanese Trace Tokenizer**: `JapaneseTraceTokenizer` primary chunk generation.
- **Protected Span handling**: dates, URLs, emails, mixed-script spans, built-in bridge/time/action patterns, and Trace DB vocabulary longest-match protection.
- **Candidate Span Generator production subset**: structurally grounded mixed-script candidate generation may be ported behind an Experimental flag. Terminal-boundary candidates should remain diagnostics only.
- **Participant Reference Normalization**: role-aware normalization after extraction using `created_by`.
- **Word / Thread / Connection model**: words, threads, word-thread links, canonical keys, strengths, seen counts, and timestamps.
- **Trace storage**: SQLite-backed repository or equivalent AIKanojyo persistence layer.
- **Activation**: raw activation from input words through trace connections.
- **Gate**: bounded selection of words, threads, and thread groups.
- **Working Memory representation**: compact recall state suitable for prompt insertion.
- **Prompt integration**: thread-group or recall-state prompt view as an Experimental prompt section.

### Research-only; do not port fully

- Oracle Evaluation.
- Oracle Replay.
- Core / Generalization / Holdout fixture loaders.
- Sensitivity runner.
- Full Research Logger.
- Benchmark SVG generation.
- CSV / Markdown report generator.

A small Diagnostics layer is still recommended in AIKanojyo. The distinction is: keep runtime counters and JSON snapshots that help compare Shadow output, but do not embed oracle labels, expected-word scoring, replay strategies, or benchmark report generation in the app.

## 3. Recommended operating modes

```text
Legacy
Trace Experimental
Shadow Evaluation
```

Start with **Shadow Evaluation**:

- Existing AIKanojyo Memory remains the production response path.
- Trace Engine runs in parallel.
- Trace extraction, saved traces, activation, gate output, and prompt candidates are logged.
- User-visible responses are not affected.

Only after Shadow logs show value should AIKanojyo test Trace Experimental prompt injection.

## 4. Phased port plan

### Phase A: Model / Storage Port

Tasks:

- Define C# models for Word, Thread, WordThreadLink / Connection, exposure/fatigue records, and gated recall DTOs.
- Add SQLite migrations that do not touch existing AIKanojyo memory tables destructively.
- Implement repository methods for word upsert, thread creation, word-thread links, canonical key lookup, and trace vocabulary export.
- Preserve `created_by` on every trace thread.
- Enforce word uniqueness and deterministic ordering.

Completion criteria:

- Existing AIKanojyo memory data survives migration.
- A test can insert an utterance and inspect words, threads, links, timestamps, and `created_by`.
- Trace vocabulary can be read without scanning all app data per turn.

### Phase B: Extractor Port

Tasks:

- Port NFKC and whitespace normalization.
- Port protected-span detection.
- Port `JapaneseTraceTokenizer` primary chunks.
- Port selected `LocalRuleTraceExtractor` rules.
- Port Participant Reference Normalization outside the extractor.
- Add the mixed-script promotion flag but keep it OFF by default.

Completion criteria:

- C# outputs are deterministic on fixed Japanese scenarios.
- Names, preferences, birthdays, dates, future plans, third-person references, corrections, and mixed-script examples are covered by unit tests.
- Extractor can run offline on Android without API calls.

### Phase C: Recall Port

Tasks:

- Port activation scoring through trace connections.
- Port gate limits and support-ratio behavior.
- Port fatigue/exposure suppression if AIKanojyo will inject Trace prompt content.
- Build a compact Working Memory object from gated recall.

Completion criteria:

- Given stored traces and a new input, AIKanojyo can produce deterministic gated recall records.
- Prompt-sized output remains bounded.
- Fatigue prevents repeated prompt spam in multi-turn tests.

### Phase D: Shadow Mode

Tasks:

- Run Trace extraction/store/recall beside the existing Memory path.
- Persist JSON diagnostics for selected turns.
- Compare Trace recall with existing recall without affecting responses.

Completion criteria:

- Shadow logs show what Trace would have recalled.
- No response behavior changes when Shadow is enabled.
- Trace failures can be diagnosed from logs.

### Phase E: Prompt A/B

Tasks:

- Add an Experimental prompt section from gated Trace Working Memory.
- A/B compare Legacy-only prompts vs Legacy + Trace prompt section.
- Track prompt token growth, irrelevant memories, relationship consistency, and answer quality.

Completion criteria:

- Trace prompt injection improves at least some target scenarios without unacceptable prompt growth or memory contamination.
- Important information such as names and birthdays is not degraded.

### Phase F: Experimental Response Mode

Tasks:

- Allow Trace output to influence responses for selected sessions or developer builds.
- Keep a runtime rollback flag.
- Continue comparing against Legacy behavior.

Completion criteria:

- 300–500 turn tests do not collapse due to irrelevant recall or prompt growth.
- Developers can disable the Trace path and return to Legacy without data loss.

## 5. Existing AIKanojyo collision checks

Before wiring Trace into responses, audit these AIKanojyo areas and choose a parallel connection point rather than replacement:

- `WorkingMemory`
- `LongTermMemory`
- Embedding Recall
- Conversation history
- Relationship Layer
- Dream
- Episode
- Emotion
- Expectation
- Inner Thought
- `PromptBuilder`
- `ChatOrchestrator`
- Diagnostics

Initial guidance: connect Trace as an additional memory candidate provider near prompt construction or memory retrieval diagnostics, not as a destructive replacement for existing long-term memory.

## 6. Do not port

- Python CLI structure.
- Benchmark-only file outputs.
- Test fixture loader.
- Oracle labels.
- Expected Word evaluation.
- Replay strategies.
- Markdown/CSV benchmark report generation.

## 7. C# porting cautions

- Python `re` and .NET `Regex` differ in Unicode behavior, escaping, and performance defaults.
- Use Unicode NFKC normalization explicitly.
- Re-check Japanese character ranges (`ぁ-ん`, `ァ-ン`, `一-龥`, `ー`) in .NET.
- Use SQLite transactions for multi-table trace writes.
- Invalidate trace vocabulary cache after word/thread writes.
- Maintain deterministic ordering for equal scores.
- Store timestamps in UTC and avoid locale-dependent parsing.
- Preserve weight precision and clamp ranges consistently.
- Use JSON diagnostics that can be enabled without shipping benchmark fixtures.
- Profile Android performance; regex backtracking and large trace vocabulary scans must be bounded.

## 8. Initial A/B scenarios

- Name: “私の名前はみつき”.
- Preference: “紅茶が好き / コーヒーは苦手”.
- Birthday: explicit birthday and later recall.
- Past conversation reference: “この前話した映画”.
- Future plan: “来週水族館に行く”.
- Third person: sibling/friend/coworker names without canonicalizing them to `@user`.
- Mixed Script: “ChatGPT Plus”, “iPhone15”, app/product names.
- Correction: “AじゃなくてB”.
- Boundary expression: “それはやめて”, “その話はしたくない”.
- Long conversation: 300–500 turns with repeated and stale topics.

## 9. Success conditions

Evaluate the integrated system, not extractor accuracy alone:

- Recalled traces feel natural and relevant.
- Prompt size does not grow beyond budget.
- Unrelated memories do not pollute responses.
- Relationship continuity improves.
- 300–500 turns remain stable.
- There are scenarios where Trace is better than existing Memory.
- Critical facts such as names and birthdays are preserved or improved.

## 10. Rollback

Trace integration must be safely disableable:

- Turning the Experimental feature OFF returns responses to existing AIKanojyo Memory.
- Migrations must not destroy or reinterpret existing memory data.
- Trace tables can remain inert if disabled.
- Shadow logs and diagnostics must not be required for normal operation.
