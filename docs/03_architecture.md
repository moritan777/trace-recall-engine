# Architecture

## High-Level Flow

```text
Conversation
  │
  ▼
Trace Extraction
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
Working Memory Candidate
  │
  ▼
Prompt
  │
  ▼
LLM
```

## Layer Responsibilities

### Trace Memory

Stores traces without meaning.

### Raw Activation

Activates words and threads from the current input.

### Recall Selection

Chooses which activated ThreadGroups should be allowed into Working Memory.

### Working Memory

Places selected trace material beside the current conversation.

### LLM

Constructs meaning and generates a response.

## Key Design Choice

The system does not pass every activated item to the LLM.

Activation may be broad.

Working Memory must be narrow.

## Extractor Evaluation Layer

Extractor research now has a standalone evaluation layer before full conversation evaluation:

```text
Extraction Boundary
↓
Extractor Evaluation
↓
Conversation Evaluation
```

This keeps extractor comparison independent from activation, gates, Working Memory, prompt views, response generation, and conversation scoring.


## Dynamic Trace Dictionary

The local-rule extractor can protect known spans using existing Trace DB words without creating an additional dictionary DB. See [Dynamic Trace Dictionary](architecture/dynamic_trace_dictionary.md).
