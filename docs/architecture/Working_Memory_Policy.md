# Working Memory Policy

Working Memory is the final selection layer before the LLM.

It is not a memory database.

It is not a cache.

It is a temporary reconstruction of the traces that appear most relevant to the current conversation.

Every response begins by rebuilding Working Memory from scratch.

---

# Position in the Architecture

```text
Conversation
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
Conversation Policy
        │
        ▼
Working Memory
        │
        ▼
LLM
```

Working Memory is the only persistent interface between the application and the LLM.

The application never sends the entire memory database.

Only the selected Working Memory is visible to the LLM.

---

# Why Working Memory Exists

Raw Activation intentionally produces more candidates than necessary.

This improves recall coverage.

However, the LLM should not receive every activated trace.

Instead, Working Memory answers a different question.

```text
Not:

"What was activated?"

But:

"What should participate in this conversation?"
```

---

# Construction Policy

Working Memory is rebuilt every turn.

Typical construction pipeline:

```text
Raw Activation

↓

Recall Selection

↓

ThreadGroup Compression

↓

Conversation Policy

↓

Working Memory
```

Nothing inside Working Memory is permanent.

The next user message may produce a completely different Working Memory.

---

# Design Principles

Working Memory should remain:

- small
- relevant
- explainable
- replaceable

It should never grow proportionally with conversation history.

The goal is stable conversational cost regardless of memory size.

---

# What Enters Working Memory

Current implementation primarily includes:

- selected ThreadGroups
- representative words
- occurrence_count
- activation score

Future implementations may also include:

- relationship signals
- temporal signals
- emotional persistence

These additions should remain structural rather than semantic.

---

# What Must Never Enter

Working Memory should never contain:

- generated summaries
- semantic labels
- rewritten memories
- application-generated interpretation

For example, the application should not produce:

```text
Mitsuki likes cheesecake.
```

Instead it should provide:

```text
ThreadGroup

key = mitsuki|like|cheesecake

occurrence_count = 3

core_words =
mitsuki
like
cheesecake
```

The LLM constructs the sentence.

The application does not.

---

# Stability

One important design objective is that Working Memory remains nearly constant even after very long conversations.

Current long-term benchmarks indicate that:

- ThreadGroup count remains compact.
- Prompt size remains stable.
- Working Memory scales independently of total conversation length.

This separation allows memory growth without proportional prompt growth.

---

# Future Research

Current research focuses on improving:

- candidate ranking
- conversation relevance
- explainability
- recall efficiency

rather than increasing the amount of information inside Working Memory.

The objective is better selection, not larger prompts.
