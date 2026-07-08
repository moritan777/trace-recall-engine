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
