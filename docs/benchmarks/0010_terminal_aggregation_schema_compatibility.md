# Terminal Aggregation Research-Log Schema Compatibility

This follow-up documents the validator-only compatibility fix for Research Logger schema v2 observations where `selected_thread_groups` and candidate entries may be serialized as either structured objects or strings.

The fix is offline-only. It does not modify Production activation, traversal, storage, Gate, Fatigue, ThreadGroup selection, Reinforcement, Working Memory, or the database schema.
