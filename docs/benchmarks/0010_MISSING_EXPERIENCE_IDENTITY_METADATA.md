# 0010 — Missing Experience Identity Metadata Research

## Summary

The clean 1000-turn count-mode fixture, its schema-v2 Research Logger output, and final SQLite snapshot were traced without changing Production. All 857 learn turns mapped to 857 stored Threads by deterministic `source_text + created_by` occurrence counts.

## Provenance and loss

The conversation fixture and eval runner contain a source turn index and input sequence. The extractor and `create_thread` API do not receive either, and the `threads` table does not persist them. This is `AVAILABLE_UPSTREAM_LOST_BEFORE_STORAGE`.

The fixture contains no source message ID, session ID, source event ID, or observation ID. Event identity is therefore `NEVER_AVAILABLE`, not merely dropped by SQLite. Research Logger schema-v2 contains ask turns only; it cannot reconstruct learn/source mapping.

## Thread creation policy

The eval runner calls `create_thread` once for each learn turn. In count mode, `create_thread` always inserts a new Thread and performs no existing-identity lookup. Weighted mode alone performs exact `canonical_key` reuse and updates strength, seen count, and last-seen time.

The identity decision boundary is the Thread factory/persistence layer. The extractor emits words, and the connection builder runs after the new Thread decision.

## Intra-turn and inter-turn repetition

| metric | result |
|---|---:|
| learn/source turns | 857 |
| mapped stored Threads | 857 |
| mapping coverage | 100% |
| turns with intra-turn duplicate signature | 0 |
| inter-turn repeated signature groups | 34 |
| same exact input groups | 34 |
| same source-text groups | 34 |
| different source / same word-set groups | 0 |

No `INTRA_TURN_DUPLICATION` was observed. All repeated groups are cross-turn exact-input repetition and also same-description/distinct-turn observations. Whether those turns refer to one event or distinct events remains `UNRESOLVABLE`.

The four largest exact-input groups contain 174, 172, 171, and 141 Thread instances respectively.

## Source-turn counterfactual

`WORD_SET + SOURCE_TURN_ID` produces 857 identities, zero repeats, and a 0% repeat ratio. This shows that source turn distinguishes observations; it does **not** show that every observation is a distinct Experience event.

The result is marked `OFFLINE_METADATA_COUNTERFACTUAL`, `production_schema_change: false`, and `recall_quality_assumption: NONE`. Message and session counterfactuals are unavailable because the fixture lacks complete identities.

## Temporal and mutable state

`date` and `created_at` are storage time; `now_iso()` has second precision. This replay stored 857 Threads across 72 unique timestamps, with 785 timestamp collisions and up to 55 Threads sharing one timestamp. Adding `created_at` to word-set identity adds 97 apparent identities, classified `TIMESTAMP_IDENTITY_ARTIFACT`, not event evidence.

Thread `seen_count`, `strength`, and `last_seen`, plus word frequency/strength, are mutable state. They are updated by weighted reuse and/or word learning/recall reinforcement and are not event identity.

## Missing metadata candidates

- `SOURCE_TURN_ID`: already exists upstream and identifies a source observation, but not an event.
- `SOURCE_EVENT_ID`: would distinguish domain events, but no upstream event semantics currently generate it.

No message/session candidate is proposed from this fixture because those identities are absent upstream. The minimal goal is not to make every Thread unique; it is to distinguish description, event occurrence, and observation using grounded provenance.

## Model arithmetic

| model | estimated identities | repeated observations | thread records | connections | status |
|---|---:|---:|---:|---:|---|
| MODEL_A_CURRENT | 857 | 692 | 857 | 2,938 | current instance storage |
| MODEL_B_DESCRIPTION_PLUS_OCCURRENCE | 857 | 692 | 857 | 2,938 | offline only |
| MODEL_C_DESCRIPTION_PLUS_SOURCE_TURN | 857 | 692 | 857 | 2,938 | offline only |
| MODEL_D_EVENT_WITH_MUTABLE_REPETITION_STATE | unknown | unknown | unknown | unknown | source event unavailable |
| MODEL_E_INSUFFICIENT_SOURCE_PROVENANCE | unknown | unknown | unknown | unknown | observed limit |

No model assumes Recall quality or changes schema.

## Integrity conclusion

Description Identity ≠ Occurrence Identity ≠ Observation Identity ≠ Mutable Repetition State. A source turn distinguishes recordings, not lived events. A storage timestamp distinguishes processing moments, not Experience identity.

## Root cause

**MULTIPLE_IDENTITY_GAPS**

- Source-turn/sequence provenance exists upstream but is lost before Thread storage.
- Event identity does not exist in the fixture or pipeline.
- Count-mode Thread creation intentionally inserts without an identity/reuse check.

## Recommended metadata direction

**SEPARATE_DESCRIPTION_AND_OCCURRENCE**

## Next recommended step

**missing identity metadataのoffline prototype**

No Production schema migration starts in this phase.
