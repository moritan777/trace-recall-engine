# Governance benchmark integrity audit

## Artificial fixture provenance

The reachable history of this checkout does not contain
`eval_governance/governance_scenarios.jsonl`: `git log --all --` has no add or
delete entry for it, and `git fsck --no-reflogs --unreachable` finds no detached
commit containing it. The branch was created from `FETCH_HEAD` at merge commit
`50f6f33` (the repository's `main` at checkout time). Therefore the earlier
Phase 2 fixture was not deleted in this history; it belongs to an unmerged or
otherwise unavailable branch difference.

Restoring a byte-for-byte fixture is intentionally not attempted from memory.
The source branch must be fetched before the artificial/captured comparison can
be treated as complete. This checkout's recorded upstream is
`https://github.com/moritan777/trace-recall-engine`; network access was blocked
by the execution environment (`CONNECT tunnel failed, response 403`).

## Test-count provenance

Commit `50f6f33` runs 72 tests. Phase 2.1 added four tests, producing 76. No test
was deleted in reachable history. The earlier claim that there were 77 tests was
a reporting error, not evidence of a missing test. Phase 2.2 adds stage-accounting
coverage, so the suite count can increase without disguising that discrepancy.

## Diagnostic accounting

Stage diagnostic events are candidate observations. The recorder currently
follows a candidate rejected at `ACTIVATION_GATE` with rejected
`RECALL_SELECTION` and `WORKING_MEMORY` observations. Consequently, counting
every rejected event produced the identical 262/262/262 totals; those were not
turn-level failures.

The evaluator now reports separately:

1. every candidate observation by stage;
2. each candidate's first suppression stage (later propagation is not counted);
3. one root-cause stage for an annotated `SHOULD_RECALL` turn that missed one or
   more expected words.

This is evaluator-only accounting and does not change runtime diagnostics or the
recall pipeline.

## Activation score event integrity

Each candidate has one `raw activation candidate` diagnostic containing its
total pre-Gate score, followed by path-level `RAW_ACTIVATION` events. An earlier
audit selected the last event by identifier and therefore reported a final
mutual-amplification path fragment (`0.0089` for turn 29) as though it were the
candidate total. Activation path analysis keeps candidate totals and individual
path contributions separate. It does not use path fragments as Gate scores.
