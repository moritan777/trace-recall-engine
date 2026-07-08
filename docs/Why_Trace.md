# Why Trace?

This project did not begin with a new algorithm.

It began with a feeling.

While developing **AIKanojyo**, we repeatedly encountered a strange problem.

The AI could remember facts.

It could retrieve previous conversations.

It could answer questions correctly.

Yet something still felt wrong.

It did not feel like the AI was *remembering*.

It felt like the AI was *searching*.

---

Most conversational memory systems today work by retrieving stored text.

```
Conversation
↓
Embedding
↓
Vector Search
↓
Retrieved Chunks
↓
LLM
```

This approach is powerful.

For factual retrieval, it often works remarkably well.

But conversations are different.

When people remember a conversation, they rarely retrieve a complete sentence.

Instead, fragments emerge.

A word.

A place.

A feeling.

A familiar topic.

Those fragments gradually reconnect until the experience becomes meaningful again.

That observation led us to a different question.

> What if conversational memory is not stored as text, but as traces?

---

In this project, a **Trace** is not a sentence.

It is not a summary.

It is not a piece of knowledge.

A Trace is simply the smallest remaining evidence that an experience once happened.

Words.

Connections between words.

Threads formed by a single experience.

Nothing more.

Meaning is intentionally **not** stored.

---

When a new conversation begins, traces become activated.

Some traces resonate more strongly than others.

Only a small number are selected.

Those selected traces enter Working Memory.

Only then does the LLM construct meaning.

```
Conversation
        │
        ▼
Trace Extraction
        │
        ▼
Trace Memory
        │
        ▼
Activation
        │
        ▼
Recall Selection
        │
        ▼
Working Memory
        │
        ▼
LLM
```

Meaning is not retrieved.

Meaning emerges.

---

One design decision gradually became the foundation of this project.

Repeated experiences are **not** merged into stronger weights.

Instead, each experience remains an independent trace.

Imagine many thin threads connecting the same ideas.

No individual thread is particularly strong.

But as more experiences accumulate, the bundle naturally becomes stronger.

Recall becomes easier—not because one connection became heavier, but because more traces now point in the same direction.

This simple mental model shaped much of the architecture presented in this repository.

---

This project does not claim that this is how the human brain works.

It does not claim to replace existing retrieval systems.

Instead, it asks a much smaller question.

> Could conversational memory emerge from traces rather than retrieved text?

Everything in this repository is an attempt to explore that question.

---

During the development of this project, we realized that the most important question was not what should an AI remember, but what should remain after an experience has faded.

We chose to call those remaining fragments Traces.
