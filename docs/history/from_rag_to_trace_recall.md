# From RAG to Trace Recall

This document records how Trace Recall Engine gradually emerged.

It is not a technical specification.

It is a research diary.

The architecture was not designed all at once.

It evolved through repeated experiments, failures, and discussions.

---

# The Beginning

This project did not begin as Trace Recall Engine.

It began during the development of **AIKanojyo**, an AI companion application.

The original goal was simple.

> Help the AI remember past conversations.

At first, the obvious solution seemed to be Retrieval-Augmented Generation (RAG).

```text
Conversation

↓

Embedding

↓

Vector Search

↓

Top-K Memories

↓

LLM
```

This approach worked.

But something always felt missing.

---

# The First Question

The AI remembered facts.

Yet conversations still felt unnatural.

The missing piece was difficult to describe.

Eventually it became one question.

> "Why does this not feel like remembering?"

The AI could retrieve information.

But retrieval did not always feel like recall.

---

# From Sentences to Words

The first experiments gradually shifted away from storing complete sentences.

Instead of asking

> "Which sentence should be retrieved?"

the project began asking

> "Which parts of previous experiences should become active?"

Words became independent nodes.

Experiences became connections.

The architecture became increasingly graph-like.

---

# The Circles and Threads

One discussion completely changed the direction of the project.

Instead of imagining memories as stored documents, we began imagining them as circles connected by threads.

```text
(Word)

──── Experience Thread ────

(Word)
```

Meaning was no longer stored.

Only traces remained.

That discussion eventually became the foundation of the Trace model.

---

# Weighted or Count?

At first, repeated experiences strengthened existing connections.

```text
Word

━━━━━━ Strength = 5
```

This became known as **Weighted mode**.

It seemed intuitive.

However, repeated conversations are not actually the same experience.

Saying

"I like cheesecake."

three different days does not erase the previous two conversations.

It creates three experiences.

That realization changed everything.

Instead of strengthening one connection,

the system preserved multiple traces.

```text
Thread 1

Thread 2

Thread 3
```

This became **Count mode**.

---

# ThreadGroup

Count mode introduced a new challenge.

Repeated traces produced repeated prompt entries.

Internally this was correct.

Externally it became inefficient.

The solution was to introduce **ThreadGroup**.

```text
Thread

Thread

Thread

↓

ThreadGroup
```

Internally, every experience remained independent.

Externally, Working Memory remained compact.

---

# Remembering is Not Speaking

Another important realization followed.

A recalled trace should not always appear in conversation.

The architecture therefore separated two different processes.

```text
Remembering

↓

Conversation
```

Topic Fatigue became the first implementation of this idea.

A trace could be remembered perfectly while still being omitted from the response.

---

# Working Memory

As the architecture grew, another layer became necessary.

The LLM should not receive:

- every stored trace
- every activated trace

Instead it should receive only:

```text
Working Memory
```

Working Memory became the final interface between the application and the LLM.

This separation dramatically reduced prompt growth while improving explainability.

---

# Long-Term Validation

The architecture was not accepted immediately.

It was repeatedly tested.

```text
100 Turns

↓

1,000 Turns

↓

3,000 Turns

↓

10,000 Turns
```

Each benchmark answered a different question.

| Benchmark | Question |
|-----------|----------|
| 100 Turns | Which storage model should survive? |
| 1,000 Turns | Does recall remain stable? |
| 3,000 Turns | Does the architecture scale? |
| 10,000 Turns | Can it operate at practical conversational scale? |

The result was not perfect precision.

The important result was that the architecture did not collapse.

Prompt size remained stable.

Working Memory remained compact.

Recall quality remained consistently high.

---

# The Shift

Somewhere during these experiments,

the project quietly stopped being "a memory experiment."

It became something else.

The central question was no longer:

> "How should memories be stored?"

It became:

> "How should traces become conversation?"

That shift changed the direction of the entire architecture.

---

# Today

Trace Recall Engine is no longer simply an experiment for AIKanojyo.

AIKanojyo remains the project's origin.

But Trace Recall Engine has gradually become an independent research project exploring trace-based conversational recall.

Its purpose is not to reproduce the human brain.

Its purpose is to ask a simple question.

> Can natural conversational recall emerge from traces rather than retrieved documents?

We still do not know the final answer.

But every benchmark, every design change, and every discussion has brought the project one step closer to asking better questions.
