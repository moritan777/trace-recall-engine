# Trace Recall Engine

> An experimental trace-based conversational memory architecture.

> **Status:** Research Prototype (Active Development)

---

## Requirements

- Python 3.11 or later
- No third-party dependencies

The current research prototype intentionally relies only on Python's standard library to keep experiments simple and reproducible.

---

## Why?

This project did not begin with a new algorithm.

It began with a feeling.

While developing **AIKanojyo**, we repeatedly encountered the same problem.

The AI could remember facts.

It could retrieve previous conversations.

It could answer correctly.

Yet something still felt wrong.

It did not feel like the AI was remembering.

It felt like the AI was searching.

That simple observation became the starting point of this project.

---

## The Question

Most conversational memory systems retrieve previously stored text.

```
Conversation
        │
        ▼
 Embedding
        │
        ▼
 Vector Search
        │
        ▼
 Retrieved Chunks
        │
        ▼
      LLM
```

This works remarkably well for factual retrieval.

But conversations are different.

Human conversations rarely return as complete sentences.

Instead, small fragments appear.

A word.

A place.

A familiar topic.

Those fragments gradually reconnect until the experience becomes meaningful again.

This project asks a simple question:

> **Can conversational memory emerge from traces rather than retrieved text?**

---

## Core Idea

Instead of storing conversations as documents, this project stores **traces**.

A trace is intentionally small.

It is not a sentence.

It is not a summary.

It is not knowledge.

It is simply evidence that an experience once happened.

When new input arrives,

those traces become activated,

a small subset is selected,

Working Memory is built,

and only then does the LLM construct meaning.

Meaning is never stored.

Meaning emerges.

---

## Architecture

```text
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

Each layer has exactly one responsibility.

---

## Design Principles

### The application does not construct meaning.

The application stores traces.

The application activates traces.

The application selects traces.

The LLM constructs meaning.

This separation of responsibilities is the central design principle of the project.

---

### Store traces, not memories.

A stored sentence already contains interpretation.

A trace does not.

The application intentionally avoids generating summaries, semantic labels, or rewritten memories before the LLM.

---

### Remembering is not speaking.

A trace may be successfully recalled.

That does not mean it belongs in the current conversation.

This distinction led to the introduction of:

- Recall Selection
- Working Memory
- Topic Fatigue

---

## Current Features

### Memory

- Trace Extraction
- Experience Threads
- Thread Groups
- Count-based Trace Reinforcement

### Recall

- Raw Activation
- Activation Gate
- Recall Selection
- Working Memory Construction

### Conversation

- Topic Fatigue
- Explainable Recall
- Prompt Optimization

### Evaluation

- Fixed conversation scenarios
- Explainable logs
- Long conversation benchmarks
- Recall Precision metrics

---

## Evaluation

The repository includes an evaluation framework.

Example:

```bash
python src/threaded_concept_memory_probe.py eval \
  --conversation-file eval_conversations/basic_recall.jsonl \
  --thread-strength-mode count
```

Current evaluation focuses on:

- Recall Precision
- Unexpected Recall
- Prompt Size
- Working Memory Size
- Recall Efficiency
- Topic Fatigue

The current goal is **not** improving storage.

The current goal is improving:

- Recall Selection
- Working Memory quality
- Conversation quality
- Long-term conversational recall

---

## Repository Layout

```text
.
├── README.md
├── LICENSE
├── src/
│   └── threaded_concept_memory_probe.py
├── docs/
├── eval_conversations/
└── reports/        # ignored local output
```

- **src/** contains the research prototype.
- **docs/** contains architecture and design documents.
- **eval_conversations/** contains reproducible evaluation scenarios.
- **reports/** stores local benchmark results and is intentionally excluded from version control.

---

## Documentation

The repository is accompanied by design documents describing the evolution of the architecture.

Topics include:

- Why Trace?
- Trace Principle
- Architecture
- Activation
- Recall Selection
- Working Memory
- Topic Fatigue
- Evaluation
- Design History
- Future Research

The documentation explains **why** the architecture looks the way it does, not only **how** it works.

---

## Origin

This project originally began as an experimental memory subsystem for **AIKanojyo**.

Over time, the research expanded beyond the original application and became an independent exploration of conversational recall.

Although the implementation may eventually be reused elsewhere, this repository focuses on the memory architecture itself.

---

## AI-assisted Development

This project is developed with extensive assistance from AI tools including ChatGPT and Codex.

Architecture, experiments, evaluation methodology, and design decisions are guided by the project maintainer through iterative discussion and benchmarking.

AI-generated code is treated as a starting point rather than a final result.

---

## Current Status

Research Prototype

Many ideas presented here remain experimental.

The purpose of this repository is not to present a finished solution, but to document an evolving line of research.

Feedback, criticism, alternative ideas, benchmark scenarios, and related research are all welcome.

---

## License

MIT License

---

## Why Continue?

This repository is not an attempt to reproduce the human brain.

It asks a much smaller question.

> **How little must an AI remember for meaningful conversational recall to emerge?**

Perhaps this architecture is wrong.

Perhaps traces are not the answer.

That is perfectly acceptable.

If this project encourages someone to ask better questions about conversational memory,

then it has already achieved one of its goals.
