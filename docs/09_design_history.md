# Design History

This project evolved through repeated disagreement and revision.

## Early Stage

The first goal was simple memory improvement for AIKanojyo.

RAG-style retrieval did not feel like remembering.

## Shift 1: From Text to Fragments

The question changed from:

> How should we retrieve text?

to:

> What remains after an experience fades?

## Shift 2: From Weight to Count

Weighted edges felt too compressed.

Repeated experiences should remain as separate traces.

This led to Count mode.

## Shift 3: From Recall to Conversation

Remembering and speaking are different.

This led to Topic Fatigue and Working Memory selection.

## Current Milestone

Trace-based Recall Engine v1.0-alpha candidate:

- Count mode adopted
- Weighted mode excluded from current scope
- ThreadGroup compression
- Explainable Recall logging
- Fatigue
- Evaluation framework
