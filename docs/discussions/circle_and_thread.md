# Discussion: Circles and Threads

The "Circles and Threads" model was not invented as a theory of the human brain.

It emerged from repeated discussions during the development of Trace Recall Engine as a simple way to think about conversational recall.

The purpose of this model is not biological accuracy.

Its purpose is architectural clarity.

---

## The First Intuition

The earliest mental image was surprisingly simple.

Words felt like circles.

Experiences felt like thin threads connecting those circles.

```text
      (みつき)
          │
          │
      (好き)
          │
          │
   (チーズケーキ)
```

Nothing in this picture carries meaning by itself.

The circles are only words.

The thread only says:

> "These words once appeared together."

---

## The Shift

Initially it was tempting to think about *stronger connections*.

Repeated conversations seemed like they should produce a thicker edge.

But something felt wrong.

If someone says

> "I like cheesecake."

every day,

it does not erase yesterday's conversation.

It creates another experience.

That led to a different interpretation.

Repeated conversations should not become one stronger thread.

They should become many separate threads.

```text
Experience 1
(みつき)──(好き)──(チーズケーキ)

Experience 2
(みつき)──(好き)──(チーズケーキ)

Experience 3
(みつき)──(好き)──(チーズケーキ)
```

Visually they appear thicker,

but internally they remain independent traces.

This became the foundation of **Count mode**.

---

## What Actually Moves?

Another important realization followed.

The circles are not what travels.

The thread is not what stores meaning.

Instead:

- Words are entry points.
- Threads carry experience.
- Activation propagates through the network.

```text
Current Input

      │

      ▼

 (好き)

      │

      ▼

 Experience Threads

      │

      ▼

(みつき)     (チーズケーキ)
```

The conversation activates the network.

The network does not retrieve complete memories.

---

## Remembering is Different from Speaking

Eventually another distinction became necessary.

A trace may be strongly activated.

That does not mean it should appear in the response.

This separation produced two different layers.

```text
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

A trace may be remembered.

Conversation policy may still decide not to speak about it.

Topic Fatigue was introduced for exactly this reason.

---

## Why This Model Exists

The Circles and Threads model is intentionally simple.

It is not intended to explain human cognition.

Instead, it provides an intuitive design language.

Whenever a new feature is proposed, we ask:

- Does it create another trace?
- Does it activate existing traces?
- Does it improve recall selection?
- Or is it trying to create meaning too early?

That question has shaped much of the architecture.

---

## Core Idea

The model can be summarized in four statements.

```text
Words are circles.

Experiences are threads.

Repeated experiences create more threads.

Meaning emerges only after selected traces reach
Working Memory and are interpreted by the LLM.
```

The goal of Trace Recall Engine is therefore not to store memories.

It is to preserve just enough traces for meaningful conversational recall to emerge later.
