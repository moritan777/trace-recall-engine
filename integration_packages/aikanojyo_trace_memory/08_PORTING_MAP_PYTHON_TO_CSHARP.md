# Python to C# Porting Map

| Python responsibility | Python source / snapshot | Proposed C# type | Notes |
|---|---|---|---|
| Extractor contract | src/trace_recall/extractors/base.py / extractor_contract.py.txt | ITraceExtractor, ExtractedTraceWord | Sync is acceptable. |
| Local rule extractor | src/trace_recall/extractors/local_rule.py / local_rule_extractor.py.txt | LocalRuleTraceExtractor | Preserve deterministic order; .NET Regex differences. |
| Tokenizer | src/trace_recall/extractors/japanese_trace_tokenizer.py / japanese_trace_tokenizer.py.txt | JapaneseTraceTokenizer | Unicode class behavior must be tested. |
| Span generator | src/trace_recall/extractors/candidate_span_generator.py / candidate_span_generator.py.txt | CandidateSpanGenerator | Diagnostic-first. |
| Participant reference | src/threaded_concept_memory_probe.py lines 717-765 / participant_reference.py.txt | ParticipantReferenceNormalizer | Keep separate from extractor. |
| Store | src/threaded_concept_memory_probe.py lines 281-716 / trace_store_schema.sql.txt | TraceMemoryRepository | SQLite; transaction per turn. |
| Recall | src/threaded_concept_memory_probe.py lines 767-1007 / recall_core.py.txt | TraceRecallService | Deterministic propagation. |
| Gate/Fatigue | src/threaded_concept_memory_probe.py lines 1009-1234 / gate_and_fatigue.py.txt | TraceRecallGate, TraceTopicFatigue | Configurable bounds/TTL. |
| WM DTO | src/threaded_concept_memory_probe.py lines 145-279 / working_memory_builder.py.txt | TraceWorkingMemoryDto | Prompt candidate only in Shadow. |
| Prompt formatter | src/threaded_concept_memory_probe.py lines 1266-1398 / prompt_formatter.py.txt | TracePromptFormatter | Do not expose internals. |
| Diagnostics | src/threaded_concept_memory_probe.py lines 1399-1468 / diagnostics_contracts.py.txt | TraceDiagnostics | JSON log for Shadow. |
