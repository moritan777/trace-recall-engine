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
