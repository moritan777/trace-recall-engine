# Why Trace?

This project did not begin with a new algorithm.

It began with a feeling.

While developing AIKanojyo, we repeatedly encountered a strange problem.

The AI could remember facts. It could retrieve previous conversations. It could answer questions correctly.

Yet something still felt wrong.

It did not feel like the AI was remembering.

It felt like the AI was searching.

## From Retrieved Text to Traces

Most conversational memory systems store text and retrieve it later.

```text
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

This works well for factual retrieval.

But conversations are different.

When people remember a conversation, they rarely retrieve a complete sentence. Instead, fragments emerge: a word, a place, a feeling, a familiar topic.

Those fragments gradually reconnect until the experience becomes meaningful again.

That observation led to a different question:

> What if conversational memory is not stored as text, but as traces?

## What is a Trace?

A Trace is not a sentence.

It is not a summary.

It is not a piece of knowledge.

A Trace is the smallest remaining evidence that an experience once happened.

- Words
- Threads formed by experiences
- Time
- Activation history

Meaning is intentionally not stored.

Meaning is reconstructed only when selected traces meet the current conversation inside Working Memory.
