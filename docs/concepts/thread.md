# Concept: Thread

A Thread represents one conversational experience.

In Count mode, repeated similar experiences create multiple threads.

The system does not merge repeated experiences into a single stronger edge.

Repeated traces accumulate.


---

## Visual Mental Model

### A Thread is one experience

A Thread should be understood as a single conversational experience rather than a permanent relationship between words.

```text
Conversation

"みつきはチーズケーキが好き"

        │
        ▼

thread_001

[みつき] ── [好き] ── [チーズケーキ]
```

### Multiple Threads

Repeated experiences remain independent.

```text
thread_001
thread_002
thread_003
        │
        ▼
ThreadGroup
occurrence_count = 3
```

Internally the traces remain separate.

Only before entering Working Memory are identical threads compressed into one ThreadGroup.

### Count vs Weighted

Weighted:

```text
One thread
strength = 3.0
```

Count:

```text
thread_001
thread_002
thread_003
```

Trace Recall Engine currently adopts the Count model because repeated conversations are treated as repeated experiences rather than a stronger stored fact.
