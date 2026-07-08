# Working Memory

Working Memory is not long-term memory.

It is the small set of selected traces placed beside the current conversation for the LLM.

## Why Working Memory Exists

Raw Activation may find many traces.

The LLM should not receive all of them.

Working Memory is the boundary between internal recall and conversational context.

## Current Format

The prompt receives ThreadGroups, not repeated raw Threads.

Example:

```text
ThreadGroup
key=みつき|チーズケーキ|好き
occurrence=6
core=みつき / 好き / チーズケーキ
```

The application does not rewrite this as:

```text
みつきはチーズケーキが好き
```

That interpretation belongs to the LLM.
