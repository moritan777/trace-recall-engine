# Concept: Trace

A Trace is the remaining evidence that an experience once happened.

It is not a sentence.

It is not a summary.

It does not contain meaning by itself.

Meaning emerges only when traces are selected and placed beside the current conversation.


---

## Visual Mental Model

### Trace as connected experience

```text
Word Nodes

[みつき]     [好き]     [チーズケーキ]
```

One experience creates one Thread.

```text
thread_001

[みつき] ── [好き] ── [チーズケーキ]
```

The application does not store the sentence itself.

It stores only the fact that these words co-occurred in one experience.

### Repeated experiences

In Count mode, repeated conversations create new Threads rather than strengthening a single edge.

```text
thread_001  [みつき] ── [好き] ── [チーズケーキ]
thread_002  [みつき] ── [好き] ── [チーズケーキ]
thread_003  [みつき] ── [好き] ── [チーズケーキ]
```

Conceptually this can be imagined as many thin threads overlapping.

```text
[みつき] ═══ [好き] ═══ [チーズケーキ]
```

The connection appears stronger not because one thread became thicker, but because more traces point in the same direction.

### Runtime activation

```text
Current Input
      │
      ▼
Word Nodes
      │
      ▼
Threads
      │
      ▼
Activated ThreadGroups
      │
      ▼
Working Memory
      │
      ▼
LLM
```

Meaning is reconstructed only after the selected traces reach Working Memory.
