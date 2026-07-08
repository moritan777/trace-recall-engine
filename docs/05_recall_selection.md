# Recall Selection

Recall Selection is the layer that decides which activated traces should move forward.

It is not the same as activation.

Activation can be noisy.

Recall Selection must be selective.

## Current Goals

- Keep expected traces
- Drop unrelated traces
- Avoid prompt bloat
- Preserve explainability
- Avoid semantic rewriting

## Inputs

- Activated Words
- Activated Threads
- ThreadGroups
- Fatigue scores
- Current input words

## Outputs

- Selected ThreadGroups
- Suppressed ThreadGroups
- Selected Words
- Suppressed Words

## Important Principle

A trace can be easy to recall but still not belong in the current conversation.
