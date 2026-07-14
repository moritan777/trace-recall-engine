# Code Reference Index

- source_snapshots/extractor_contract.py.txt: ExtractedWord, TraceExtractor, normalization, dedupe. Port with stable ordering and clamp behavior.
- source_snapshots/local_rule_extractor.py.txt: final extraction selection, protected spans, mixed-script promotion flag, diagnostics.
- source_snapshots/japanese_trace_tokenizer.py.txt: primary chunks and alternate diagnostics; not morphology.
- source_snapshots/candidate_span_generator.py.txt: diagnostic mixed-script and terminal-boundary candidates.
- source_snapshots/participant_reference.py.txt: created_by-based @user/@assistant normalization.
- source_snapshots/trace_store_schema.sql.txt: schema, repository methods, cache, exposure storage.
- source_snapshots/recall_core.py.txt: activation service and scoring.
- source_snapshots/gate_and_fatigue.py.txt: prompt bounds, fatigue suppression, ThreadGroup grouping.
- source_snapshots/working_memory_builder.py.txt: dataclass DTOs for activated/gated context.
- source_snapshots/prompt_formatter.py.txt: threadgroup, recall-state, edge views and prompt text.
- source_snapshots/diagnostics_contracts.py.txt: console diagnostic shape to convert to JSON logs.
