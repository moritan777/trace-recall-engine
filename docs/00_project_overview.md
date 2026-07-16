# Project Overview

Trace Recall Engine is a research prototype for exploring trace-based conversational recall.

It began as part of AIKanojyo memory research, but it has grown into an independent experiment around one question:

> Can conversational memory emerge from traces rather than retrieved text?

The project is not intended to reproduce the human brain. It is a practical research system for testing whether traces, activation, recall selection, and working memory can produce more natural long-term conversational recall.

For the story behind this project, see

📝 Development Story (note)

For technical discussions

📖 Zenn

## Current Status

- Status: Research Prototype
- Storage mode: Count-based trace accumulation
- Weighted mode: research comparison ended
- Main focus: Recall Selection, Working Memory loading, Conversation Policy, and evaluation

## Core Pipeline

```text
Conversation
↓
Trace Extraction
↓
Trace Memory
↓
Raw Activation
↓
Recall Selection
↓
Working Memory
↓
LLM
↓
Response
```
