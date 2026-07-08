# Trace Principle

## Core Statement

Trace Recall Engine does not store meaning.

It stores traces that may later become meaningful.

Meaning is not a database record. Meaning emerges at runtime when the LLM combines:

- Current input
- Recent conversation
- Selected traces

## What the Application Does

The application may:

- Store traces
- Activate traces
- Select traces
- Suppress over-exposed traces
- Load selected traces into Working Memory

The application must not:

- Generate emotional meaning
- Rewrite traces as summaries
- Decide that a trace is important because it feels meaningful
- Convert traces into natural-language memories before the LLM sees them

## Why This Matters

A stored sentence already contains interpretation.

A trace does not.

This distinction keeps the architecture aligned with the principle:

> The application organizes information. The LLM constructs meaning.
