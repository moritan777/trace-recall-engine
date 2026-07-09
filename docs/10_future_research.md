# Future Research

The current architecture has completed its initial storage and long-term scalability validation.

Future work focuses less on **how traces are stored**, and more on **how recalled traces contribute to conversation**.

---

## Phase 1 — Recall Quality

The storage model is now considered sufficiently stable.

Current research focuses on improving recall itself.

- Improve Recall Selection
- Improve Working Memory policy
- Improve Explainable Recall
- Improve response-aware Recall Efficiency
- Add long-distance recall scenarios
- Add multi-person confusion tests

---

## Phase 2 — Trace Extraction

Current trace extraction relies on an LLM.

Future work will investigate lighter alternatives.

- Compare LLM extraction with local keyword extraction
- Evaluate rule-assisted extraction
- Explore language-independent extraction interfaces
- Reduce inference cost while preserving recall quality

The goal is not to eliminate the LLM, but to reduce unnecessary dependence on it.

---

## Phase 3 — Conversation

Recall is only useful if it improves conversation.

Future evaluation will measure:

- Whether recalled traces are actually used by the LLM
- Whether recalled traces improve conversational consistency
- Whether Topic Fatigue produces more natural dialogue
- Whether Working Memory remains compact during long conversations

---

## Phase 4 — Applications

Trace Recall Engine is intended to become a reusable recall architecture.

Possible applications include:

- AIKanojyo
- Standalone conversational companions
- Experimental conversational memory systems
- Research platforms for explainable recall

---

## Long-Term Vision

The long-term goal is not to reproduce human memory.

The goal is to explore whether conversational memory can emerge from:

```text
Trace
        ↓
Activation
        ↓
Recall Selection
        ↓
Working Memory
        ↓
LLM
```

rather than traditional document retrieval.

Future work will continue to evaluate this hypothesis through reproducible benchmarks and open research discussions.
