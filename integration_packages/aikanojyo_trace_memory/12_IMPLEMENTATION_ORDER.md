# Implementation Order

## PR 1: Architecture Audit
Report existing Memory path and integration points. No code changes.

## PR 2: Trace Models + Migration
Add DTO/entity/SQLite tables/repository. No runtime use. Must not touch existing data.

## PR 3: Extractor Port
Port normalizer, tokenizer, local rule, participant reference, and unit tests. No external dependency.

## PR 4: Trace Save Shadow
Save per conversation turn and diagnostics. Do not use in production prompt.

## PR 5: Recall Port
Activation, selection, gate, fatigue. Deterministic outputs and bounded sizes.

## PR 6: Shadow Comparison
Existing vs Trace logs and metrics: overlap, only-existing, only-trace, empty, noise, misses.

## PR 7: Prompt Candidate Preview
Render candidates for diagnostics/UI only; no production prompt insertion.

## PR 8: Experimental Prompt A/B
Feature flag, default OFF, rollback path, controlled evaluation.
