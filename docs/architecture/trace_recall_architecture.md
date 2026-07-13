# Trace Recall Architecture

Trace Recall Engine is organized as a sequence of independent layers.

Each layer has exactly one responsibility.

The purpose of this separation is to make conversational recall explainable, testable, and replaceable without affecting the rest of the architecture.

Unlike traditional retrieval systems, Trace Recall Engine does not retrieve complete memories.

Instead, it progressively transforms conversational traces into a small Working Memory that can be interpreted by the LLM.

---

# Overview

```text
Conversation
        │
        ▼
Trace Extraction [replaceable]
        │
        ▼
Trace Memory
        │
        ▼
Raw Activation
        │
        ▼
Recall Selection
        │
        ▼
ThreadGroup Compression
        │
        ▼
Conversation Policy
        │
        ▼
Working Memory
        │
        ▼
LLM
        │
        ▼
Response
```

Each stage performs one clearly defined task.

---

# Layer 1 — Trace Extraction

Input conversation is converted into traces.

The extractor does **not** attempt to understand meaning.

Instead it extracts structural elements that may later participate in recall.

Examples include:

- words
- co-occurrence
- thread membership
- canonical keys

The extractor should remain lightweight whenever possible.

The current research Baseline uses an Implemented LLM Extractor when an endpoint is configured. Without an endpoint, or when `--extractor fallback` is selected, the implementation uses the Implemented diagnostic fallback extraction path.

Extraction is intentionally treated as a replaceable boundary under `src/trace_recall/extractors/`. The recall pipeline depends on the common extractor contract rather than one specific extraction method.

The next research phase will compare the current LLM Extractor with deterministic local alternatives while keeping Trace Memory, Raw Activation, Recall Selection, Working Memory, and prompt generation fixed. A Trace-specific Local Rule Extractor is Planned; morphological-analysis-assisted extraction remains a Candidate and is not selected.

---

# Layer 2 — Trace Memory

Trace Memory is the persistent storage.

It stores:

- Word Nodes
- Experience Threads
- Thread Groups (derived)
- Connection history

Meaning is intentionally absent.

The database remembers only that experiences happened.

---

# Layer 3 — Raw Activation

Current input activates nearby traces.

Activation is intentionally broad.

Noise is acceptable at this stage.

Its purpose is to avoid missing potentially useful traces.

Raw Activation answers one question:

> "What might be relevant?"

It does **not** answer:

> "What should be used?"

---

# Layer 4 — Recall Selection

Recall Selection reduces the activated search space.

Its responsibilities include:

- ranking
- filtering
- suppression
- ThreadGroup creation

This stage transforms:

```text
Many activated traces

↓

Small candidate set
```

This is the first stage where precision becomes important.

---

# Layer 5 — ThreadGroup Compression

Repeated experiences remain independent inside Trace Memory.

Before entering Working Memory they are compressed.

```text
Thread
Thread
Thread
Thread

↓

ThreadGroup
```

This keeps prompt size nearly constant while preserving repeated experiences internally.

Count mode depends on this layer.

---

# Layer 6 — Conversation Policy

Even correctly recalled traces should not always appear.

Conversation Policy decides whether recalled information should actually participate in the response.

Current policies include:

- Topic Fatigue
- Asked Override

Future policies may include:

- relationship-aware selection
- emotional persistence
- dialogue pacing

Conversation Policy separates:

```text
Remembering

↓

Speaking
```

These are intentionally different problems.

---

# Layer 7 — Working Memory

Working Memory is temporary.

It contains only the traces selected for the current response.

Working Memory is rebuilt every turn.

Nothing inside Working Memory is permanently stored.

Its purpose is to provide the LLM with just enough context to reconstruct meaning.

---

# Layer 8 — LLM

The LLM performs:

- interpretation
- reasoning
- natural language generation

The LLM is the only component that constructs meaning.

The application never attempts to replace this process.

---

# Design Philosophy

The architecture follows one guiding principle.

```text
Store traces.

Never store meaning.

Activate widely.

Select carefully.

Speak selectively.

Construct meaning only inside the LLM.
```

Every new feature should strengthen one layer without expanding its responsibilities.

## Local Rule Extractor v0 Status

LLM Extractor is the current baseline; fallback remains a diagnostic path. Local Rule Extractor v0 is now an experimental deterministic local candidate: it uses no morphological analyzer, no external API, and is not integrated with Android yet.

## Japanese Trace Tokenizer Layer

The local deterministic extraction path separates token candidate generation from local-rule selection:

```text
Surface Normalize
↓
Protected Span
↓
Japanese Trace Tokenizer
↓
Local Rule Selection
↓
Noise Filter
↓
Participant Reference
```

`JapaneseTraceTokenizer` is not a morphological analyzer. It does not infer meaning, part of speech, intent, emotion, preferences, people, or relationships. Its responsibility is only to preserve protected spans and propose recall-oriented surface chunks from sentence, clause, and phrase boundaries. Local rules then choose final Trace words from those candidates.

The tokenizer is intentionally recall-oriented: when a boundary is uncertain, it prefers keeping a longer unknown phrase over breaking a possible Trace name or compound.

## Tokenizer Candidate Oracle

The Japanese Trace Tokenizer now has two observational outputs:

- **Primary Chunks**: the existing tokenizer output consumed by Local Rule selection.
- **Alternate Spans**: bounded diagnostic candidates generated from script boundaries, particle/connective boundaries, sentence punctuation, protected-span boundaries, and existing tokenizer boundaries.

Alternate Spans do not replace Primary Chunks and are not a new selector. They are recorded so extractor evaluation can prove whether an expected word was generated by the tokenizer candidate layer, generated only as an alternate, selected into final output, or never generated.

Extractor evaluation records an Oracle Result per expected word with statuses such as `final`, `primary_only`, `alternate_only`, and `missing`. This keeps the research phase focused on measurement before selector optimization.

### Candidate Span Generator v2

Candidate Span Generator v2 adds only structurally grounded Mixed Script and safe terminal-boundary candidates. New candidates remain diagnostic-only and are not promoted to production extraction output. Oracle Replay is reused to test generalization before any selector change.

The generator records candidate `source` and `reason` metadata for oracle diagnostics while keeping final words, trace persistence, and recall behavior unchanged.
