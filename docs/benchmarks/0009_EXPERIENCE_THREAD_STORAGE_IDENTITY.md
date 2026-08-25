# 0009 — Experience Thread Storage Identity Analysis

## Summary

The unchanged 100/1000-turn count-mode baseline was analyzed at five offline identity levels. No identity key, deduplication, upsert, merge, schema, learning, Recall, or reinforcement behavior was implemented.

## Identity collapse

1000-turn results:

| identity level | unique identities | repeat instances | repeat ratio | max repetition | information gain |
|---|---:|---:|---:|---:|---:|
| LEVEL_0_WORD_SET | 165 | 692 | 80.75% | 174 | — |
| LEVEL_1_SOURCE_TEXT | 165 | 692 | 80.75% | 174 | 0.00% |
| LEVEL_2_ORIGIN | 165 | 692 | 80.75% | 174 | 0.00% |
| LEVEL_3_TEMPORAL_STATE | 220 | 637 | 74.33% | 46 | 7.95% |
| LEVEL_4_STRENGTH_STATE | 220 | 637 | 74.33% | 46 | 0.00% |

Source text and origin do not distinguish any additional identities in this fixture. Temporal fields split 55 identities, but strength state adds no further split.

## State differences and temporal identity

Among repeated LEVEL_0 groups, the only observed differing fields in this replay are `created_at` and `last_seen`, each in 25 groups. Both derive from observation/storage time in the current code; `date` is also generated from that storage timestamp. The temporal split is therefore classified `TIMESTAMP_UNIQUENESS_ARTIFACT`, not evidence of distinct lived events.

Timestamp equality depends on storage-time resolution and replay timing. Consequently, counts of state-equivalent groups can vary between clean replays even when Production configuration and conversation fixtures are unchanged. This reinforces why storage timestamps are not a sufficient Experience identity.

## Identity versus state roles

Canonical word set, canonical key, source text, and utterance origin are offline `IDENTITY_CANDIDATE` fields. `last_seen`, `seen_count`, and `strength` are `MUTABLE_STATE_CANDIDATE` fields. Storage-derived `date`/`created_at` and connection `weight_in_thread` remain `UNKNOWN_ROLE` for Experience identity.

Current docs intentionally describe count mode as preserving repeated conversations as separate countable traces. Word frequency, thread repetition, mutable strength, and connection multiplicity can therefore coexist; this is recorded as `POTENTIAL_REDUNDANT_REPETITION_REPRESENTATION`, not a bug.

## Recall and instance utility

Annotated expected/unexpected thread-path coverage is 15.58%. Twenty-two repeated LEVEL_0 groups contain more than one instance with an observed expected-target path contribution. That shows multiple stored instances participate in the current topology; it does not establish that all instances are independently necessary for quality.

The mean top-instance path share among observed repeated groups is 55.38%, with a range from 1.03% to 100%. Utility is therefore not uniformly concentrated in either one dominant instance or all instances.

## Connection equivalence

All 34 repeated LEVEL_0 groups have `IDENTICAL_CONNECTION_SET`, as expected for groups defined by the same canonical word set. There are no observed partial or different connection sets within those groups.

## Offline model counterfactuals

| model | identities | repeat-state updates | connections | observed path opportunities | repeated path opportunities | mean fanout |
|---|---:|---:|---:|---:|---:|---:|
| MODEL_A_INSTANCE_IDENTITY | 857 | 0 | 2,938 | 68,987 | 0 | 33.39 |
| MODEL_B_STRUCTURAL_IDENTITY | 165 | 692 | 683 | 17,200 | 51,787 | 7.76 |
| MODEL_C_CONTENT_ORIGIN_IDENTITY | 165 | 692 | 683 | 17,200 | 51,787 | 7.76 |
| MODEL_D_STRUCTURAL_WITH_MUTABLE_STATE | 165 | 692 | 683 | 17,200 | 51,787 | 7.76 |
| MODEL_E_UNRESOLVED | unknown | unknown | unknown | unknown | unknown | unknown |

Every row is `OFFLINE_IDENTITY_COUNTERFACTUAL`, with `production_replay: false` and `recall_quality_assumption: NONE`. Model B/C/D coincide because source text and origin add no split in this fixture.

For the highest-fanout word `した`, connected identities change arithmetically from 199 under instance identity to 50 under Models B/C/D. No Activation score or Recall quality is recomputed.

## Safety

Instance identity risks over-separation and unknown Recall impact. Structural models risk temporal/state/repetition-strength collapse and unknown Recall impact. The unresolved model leaves every requested safety dimension unknown. No candidate is safe for automatic Production adoption from this evidence.

## Integrity conclusion

- Same word set is not proof of the same Experience.
- Same Experience is not proof of the same state.
- Repeating one Experience is not proof that multiple Experiences exist.
- Storage timestamp uniqueness is not event identity.
- Expected labels are used only by the utility overlay, never by identity grouping.

## Identity classification

**IDENTITY_METADATA_INSUFFICIENT**

Existing fields distinguish structural descriptions and mutable storage state but do not establish whether an identical description is the same recorded event, a later distinct event, or a repeated observation of one Experience.

## Recommended storage direction

**ADD_MISSING_IDENTITY_METADATA**

## Next research step

**missing metadata研究**

Production migration does not start in this phase.
