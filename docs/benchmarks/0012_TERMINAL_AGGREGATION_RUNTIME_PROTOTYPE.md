# Terminal Aggregation Runtime Prototype

## Scope

This phase moves the already validated terminal-edge arithmetic equivalence into an **opt-in Production-compatible runtime prototype**.

The normal entrypoint `src/threaded_concept_memory_probe.py` remains unchanged and therefore terminal aggregation is **default OFF**.  The prototype is enabled only by running:

```text
src/threaded_concept_memory_probe_terminal_aggregation.py
```

The prototype changes only repeated arithmetic on the final `word -> thread` hop at `max_depth`.  It does **not** change:

- Experience Thread storage or identity
- Word/Thread connections
- count semantics
- traversal depth
- pre-terminal propagation
- Activation Gate policy
- ThreadGroup selection
- Fatigue
- Reinforcement
- Working Memory policy
- DB schema

## Runtime boundary

All physical scores that reach the same terminal Word node are retained as provenance cardinality.  For each distinct outgoing `(word, thread)` terminal edge, the invariant edge factor is applied to the accepted source-score aggregate once instead of repeating the same terminal edge arithmetic for every physical path.

The existing per-physical-path `0.001` admission boundary is preserved by converting it to incoming-score space before aggregation.

The runtime reports:

- physical terminal paths
- distinct terminal edges
- operations saved
- aggregation ratio
- maximum edge multiplicity
- cumulative prototype activation elapsed time

Aggregated trace records retain the physical contributor multiplicity in their reason string.

## Validation status before this prototype

The Phase 3.6 1000T Research Logger replay established:

- 143 / 143 ask turns downstream-equivalent
- 1,338,768 physical terminal paths
- 61,147 distinct terminal edges
- aggregation ratio about 21.894x
- provenance preserved
- maximum numeric delta about 1.78e-14

That was offline validation.  This prototype exists to measure whether the same boundary produces a real runtime latency reduction without changing recall behavior.

## Required benchmark sequence

1. Run the normal entrypoint on a clean 100T DB.
2. Run the opt-in prototype entrypoint on a separate clean 100T DB with otherwise identical arguments.
3. Compare Recall/Gate/Working-Memory quality metrics and recall/end-to-end latency.
4. Proceed to 1000T only if 100T has no behavioral regression.
5. Do not make the prototype default ON until 1000T confirms both behavioral equivalence and useful runtime improvement.

`terminal aggregation != memory deletion`, `arithmetic aggregation != thread merge`, and `offline equivalence != Production performance improvement` remain explicit integrity rules.
