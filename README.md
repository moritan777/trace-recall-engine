# Trace Recall Engine (Research)

> An experimental trace-based memory architecture for conversational AI.

> **Status:** Research Prototype (Active Development)

---


## Repository Layout

```
.
├── README.md
├── LICENSE
├── src/
│   └── threaded_concept_memory_probe.py
├── docs/
├── eval_conversations/
└── reports/        # ignored local output
```

- `src/` contains the Python research prototype.
- `docs/` is reserved for public-facing design and methodology notes.
- `eval_conversations/` is the place for JSONL evaluation fixtures.
- `reports/` is intentionally ignored for local run outputs.

---

## Why this project exists

Most conversational memory systems store text and retrieve it later.

Typical pipelines look like this:

```

Conversation
↓
Embedding
↓
Vector Search
↓
Top-K Chunks
↓
LLM

```

This works well for factual retrieval.

However, during the development of **AIKanojyo**, an AI companion application, one recurring question appeared:

> **"Is this really how humans remember conversations?"**

That question led to this project.

---

## Core Idea

Instead of storing conversations as retrievable text chunks, this project explores a different hypothesis.

A conversation leaves behind **traces**.

Those traces can later become activated by new input.

Only a small subset of activated traces should enter Working Memory.

Meaning is **not stored**.

Meaning is reconstructed only when the LLM combines:

- Current input
- Recent conversation
- Selected traces

This architecture is called **Trace-based Recall**.

---

## Architecture

```

Conversation
│
▼
Trace Extraction
│
▼
Trace Memory
├── Word Nodes
├── Experience Threads
├── Thread Groups
└── Connection History
│
▼
Raw Activation
│
▼
Recall Selection
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

---

## Design Principles

### AIKanojyo does not store meaning.

It stores only traces that may later become meaningful.

The application intentionally does **not** generate summaries, semantic labels, or rewritten memories.

Only the LLM constructs meaning.

---

### Separation of Responsibilities

Memory Layer

- Store traces
- Strengthen traces
- Forget traces

Recall Layer

- Activate traces
- Select relevant traces
- Build Working Memory candidates

LLM

- Interpret
- Reason
- Generate natural language

Each layer has a single responsibility.

---

## Current Features

- Trace extraction
- Word-based activation
- Experience Threads
- Thread Groups
- Count-based trace reinforcement
- Activation Gate
- Working Memory selection
- Topic Fatigue
- Explainable Recall logging
- Evaluation framework
- Long conversation benchmarks

---

## Evaluation

The project includes an evaluation mode.

```

python src/threaded_concept_memory_probe.py eval \
  --conversation-file eval_conversations/basic_recall.jsonl \
  --thread-strength-mode count

```

Evaluation metrics include:

- Recall Precision
- Unexpected Recall
- Working Memory size
- Prompt size
- Topic Fatigue
- Recall Efficiency
- Explainable Recall logs

---

## Current Research Status

Current focus is **not** memory storage.

Current research focuses on:

- Recall Selection
- Working Memory loading
- Conversation policy
- Long-term recall
- Explainable memory

---

## Philosophy

Traditional RAG retrieves stored text.

This project explores a different hypothesis.

```

Stored Text
↓

Retrieved Text
↓

LLM

```

vs.

```

Stored Traces
↓

Activation
↓

Recall Selection
↓

Working Memory
↓

LLM

```

The hypothesis is that conversational memory may emerge from traces rather than retrieved documents.

---

## Origin

This project originated during the development of **AIKanojyo**.

It has since evolved into an independent research project exploring trace-based conversational recall architectures.

---

## AI-assisted Development

This project is developed with extensive assistance from AI tools including ChatGPT and Codex.

The architecture, evaluation methodology, and research direction are guided by the project maintainer.

AI-generated implementations are accepted only after iterative discussion, benchmarking, and evaluation.

---

## Current Status

Research Prototype

Many design decisions remain experimental.

Feedback, discussions, criticism, benchmark ideas and related research are all welcome.

---

## License

MIT License

---

## Why?

This repository is not an attempt to reproduce the human brain.

It is an attempt to ask a simple question:

"How little must an AI remember for meaningful recall to emerge?"
