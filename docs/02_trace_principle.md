# Trace Principle

Trace Recall Engine is built around one simple principle.

> **Meaning should not be stored. Meaning should emerge.**

The application is responsible for preserving traces.

The LLM is responsible for constructing meaning.

Everything else in the architecture follows from this separation.

---

## What is a Trace?

A Trace is not a sentence.

It is not a summary.

It is not knowledge.

It is the smallest remaining evidence that an experience once happened.

A trace may contain:

- Words
- Experience Threads
- Thread Groups
- Activation history
- Conversation exposure

None of these elements contains meaning by itself.

Meaning only appears when selected traces meet the current conversation inside Working Memory.

---

## Responsibilities

### The Application

The application may:

- Store traces
- Strengthen repeated traces
- Activate traces
- Select traces
- Suppress over-exposed traces
- Build Working Memory

The application must **not**:

- Interpret emotions
- Decide semantic importance
- Rewrite traces into summaries
- Generate natural-language memories
- Decide what a trace "means"

---

### The LLM

The LLM receives:

- Current input
- Recent conversation
- Working Memory

From these, it:

- Interprets
- Reasons
- Generates natural language

Meaning is therefore a runtime phenomenon.

It is never persisted.

---

## Why This Separation Matters

A stored sentence already contains interpretation.

A trace does not.

This distinction makes it possible to separate:

```text
Storage
        ↓
Activation
        ↓
Recall Selection
        ↓
Working Memory
        ↓
Meaning Construction
````

Each layer has exactly one responsibility.

---

## Trace Principle

The architecture can be summarized in six rules.

```text
Store traces.

Never store meaning.

Activation is not recall.

Recall is not conversation.

Working Memory is temporary.

Meaning emerges only inside the LLM.
```

Every new feature should be evaluated against these rules.

If a proposed feature requires the application to generate meaning before the LLM, it probably violates the Trace Principle.

````
