# Topic Fatigue

Topic Fatigue separates remembering from speaking.

A trace may be strongly recalled, but if it has appeared too often recently, it may be suppressed from Working Memory.

## Core Idea

```text
Trace Strength = how easily it is recalled
Topic Fatigue = how repetitive it would feel in conversation
```

These are different.

## Example

A user may love cheesecake.

The system should remember that strongly.

But it should not mention cheesecake every day unless the user asks.

## Current Implementation

The system records exposure events:

- prompt exposure
- response exposure

Prompt exposure is currently used for suppression. Response exposure is prepared for future refinement.

## Asked Override

If the user explicitly asks about a word, fatigue should not suppress it.
