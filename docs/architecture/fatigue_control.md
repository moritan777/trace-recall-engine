# Fatigue Control

Topic Fatigue prevents repetitive conversation.

Its purpose is not to weaken memory.

Its purpose is to improve dialogue.

A trace may be remembered perfectly while still being omitted from the current response.

---

# Position in the Architecture

```text
Raw Activation
        │
        ▼
Recall Selection
        │
        ▼
ThreadGroup
        │
        ▼
Topic Fatigue
        │
        ▼
Working Memory
```

Topic Fatigue operates after recall has already succeeded.

It therefore affects conversation rather than memory.

---

# Remembering vs Speaking

One of the central ideas of Trace Recall Engine is:

```text
Remembering

≠

Speaking
```

These are intentionally different processes.

A trace can be:

- activated
- recalled
- selected

and still not appear in the response.

---

# Why Fatigue Exists

Without suppression, strongly connected traces would appear repeatedly.

For example:

```text
User likes cheesecake.

↓

Cheesecake becomes highly recallable.

↓

Every conversation mentions cheesecake.
```

Although technically correct, this quickly feels unnatural.

Human conversation usually avoids unnecessary repetition.

---

# Exposure

Current implementation records conversational exposure.

Two exposure types exist.

```text
Prompt Exposure

The trace entered Working Memory.
```

```text
Response Exposure

The trace actually appeared in the generated response.
```

Current suppression mainly uses Prompt Exposure.

Response Exposure is included to support future refinements.

---

# Asked Override

Topic Fatigue must never prevent direct answers.

Example:

```text
User:

What is my favorite cake?
```

Even if:

```text
Cheesecake
```

has recently appeared many times,

it should still be included.

Explicit user intent always overrides fatigue.

---

# Design Principles

Topic Fatigue should:

- reduce repetition
- preserve memory
- remain explainable
- remain deterministic

It should never erase traces.

It only influences whether they participate in the current Working Memory.

---

# Explainability

Every suppression should be observable.

Current logs include:

```text
Word

Prompt Fatigue

Response Fatigue

Suppressed

Reason
```

Future versions may additionally visualize suppression history across conversations.

---

# Future Research

Possible extensions include:

- relationship-aware fatigue
- emotional fatigue
- temporal decay
- user-specific conversation pacing
- adaptive suppression thresholds

The goal is not to forget more.

The goal is to speak more naturally.
