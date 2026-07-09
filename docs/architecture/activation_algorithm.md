# Activation Algorithm

Activation is the first dynamic stage of Trace Recall Engine.

Its goal is not to retrieve memories.

Its goal is to discover which traces may become relevant.

---

# Basic Flow

```text
Current Input

↓

Input Words

↓

Word Nodes

↓

Experience Threads

↓

Additional Word Nodes

↓

Activated Threads

↓

Activated ThreadGroups
```

Activation spreads through the trace network.

This process resembles propagation rather than search.

---

# Why Activation Comes First

Traditional retrieval systems usually perform:

```text
Query

↓

Search

↓

Top-K
```

Trace Recall Engine instead performs:

```text
Input

↓

Activation

↓

Selection
```

The distinction is important.

Activation intentionally accepts noise.

Selection removes it later.

---

# Activation Sources

Current activation may originate from:

- direct word matches
- connected threads
- shared ThreadGroups

Future work may include:

- temporal activation
- relationship activation
- emotional activation

---

# Activation Is Not Recall

One of the core principles of the architecture is:

```text
Activation ≠ Recall
```

A trace may become activated without entering Working Memory.

Example:

```text
Input

↓

チーズケーキ

↓

Activated

カフェ
好き
帰り道
映画
```

Many traces become active.

Only a few continue.

---

# Explainability

Every activation should be observable.

Current logs include:

- activated words
- activated threads
- activated ThreadGroups

Future versions may visualize complete propagation paths.

---

# Why Noise Is Allowed

The activation stage intentionally favors recall over precision.

False positives are acceptable.

False negatives are more harmful.

Selection is responsible for removing unnecessary candidates.

---

# Future Work

Potential research topics include:

- adaptive propagation depth
- activation decay
- activation path visualization
- graph-based propagation strategies
- language-independent activation interfaces

Activation is therefore an exploration stage rather than a retrieval stage.
