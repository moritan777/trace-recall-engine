# Current Handover

Last updated: 2026-07-14 UTC.

## 1. Current location

- Branch: `work`.
- Commit at documentation creation: `54d6ea2`.
- Current extractor options: `llm`, `fallback`, `local-rule`.
- Current Local Rule extractor: `LocalRuleTraceExtractor` in `src/trace_recall/extractors/local_rule.py`.
- Experimental flag: `--enable-mixed-script-promotion`, default OFF.
- Main CLI: `src/threaded_concept_memory_probe.py` with commands `add`, `ask`, `threads`, `words`, `bootstrap-identity`, `seed-tests`, `chat`, `config`, `prompt-preview`, `eval-extractor`, `oracle-replay`, `eval`, and `sensitivity`.
- Latest temporary evaluation state: core is strong, generalization drops, holdout exposes limits; mixed-script promotion improves mixed-script A/B but is not adopted by default.

## 2. Implemented now

Verified in the current repository:

- Replaceable extractor boundary: `TraceExtractor` protocol.
- `LLMTraceExtractor` baseline.
- `FallbackTraceExtractor` diagnostic fallback.
- `LocalRuleTraceExtractor` deterministic experimental extractor.
- Surface normalization in Local Rule extraction.
- Protected spans for trace dictionary, built-in bridge/time/action words, URLs, email, dates, mixed script, and compound-like spans.
- `JapaneseTraceTokenizer` primary chunks and alternate diagnostics.
- `CandidateSpanGenerator` v2 mixed-script and terminal-boundary diagnostic candidates.
- Mixed-script promotion flag for Local Rule extraction, disabled by default.
- Participant Reference Normalization outside extractor boundary.
- SQLite Trace Store with words, threads, word-thread links, exposure records, `created_by`, canonical keys, strength, weight, and seen counts.
- Dynamic Trace Dictionary via `get_trace_vocabulary()`.
- Activation, gate, fatigue/exposure handling, Working Memory prompt views, and response prompt construction.
- Extractor evaluation, oracle evaluation, oracle replay, conversation evaluation, sensitivity runner, and Research Logger style outputs.

## 3. Not implemented

- AIKanojyo C# port.
- AIKanojyo Shadow Mode.
- AIKanojyo DB / Recall full A/B.
- AIKanojyo Prompt integration.
- Long-term real conversation evaluation inside AIKanojyo.
- Production selector for all alternate spans.
- Production terminal-boundary promotion.
- Category-specific selector or learned candidate classifier.

## 4. Known constraints

- Generalization benchmark is much weaker than the core fixture.
- Holdout benchmark shows substantial tokenizer loss and selector loss.
- Mixed Script Promotion has A/B gains but no dataset-level production decision.
- Terminal Boundary candidates are noisy and diagnostic only.
- Participant Reference Normalization does not solve every ambiguity or identity-specific reference.
- This is not a perfect Japanese segmentation system.
- Current evaluation fixtures are research tools; they are not real AIKanojyo production logs.

## 5. Next work, in priority order

1. Audit AIKanojyo's current Memory architecture.
2. Decide where Trace Engine can run in parallel without replacing existing Memory.
3. Design the C# storage model and SQLite migration.
4. Implement Shadow Mode.
5. Port Extractor components to C#.
6. Port Recall / Activation / Gate components to C#.
7. Run Prompt A/B with bounded Trace Working Memory.
8. Evaluate on real long conversation logs.

## 6. Do not do next

- Do not immediately delete existing AIKanojyo Memory.
- Do not switch the default response path to Trace.
- Do not port Oracle / Replay into the app.
- Do not wait for 100% extractor accuracy before integration.
- Do not add dictionaries or rules without real conversation evidence.

## 7. First reading order for the next assignee

1. `docs/handover/AIKANOJYO_MEMORY_ENGINE_BIBLE.md`
2. `docs/handover/AIKANOJYO_INTEGRATION_GUIDE.md`
3. `docs/handover/CURRENT_HANDOVER.md`
4. `docs/research/current_research_direction.md`
5. `docs/research/extractor_research_plan.md`
6. `docs/research/extractor_evaluation.md`
7. `docs/architecture/trace_recall_architecture.md`
8. `docs/architecture/dynamic_trace_dictionary.md`
9. `docs/09_design_history.md`
10. `docs/10_future_research.md`

## 8. Existing documents checked for this handover

- `README.md`
- `docs/README.md`
- `docs/getting_started.md`
- `docs/architecture/trace_recall_architecture.md`
- `docs/architecture/dynamic_trace_dictionary.md`
- `docs/research/current_research_direction.md`
- `docs/research/extractor_research_plan.md`
- `docs/research/extractor_evaluation.md`
- `docs/09_design_history.md`
- `docs/10_future_research.md`
- `eval_extractors/README.md`
- `eval_extractors/extractor_core_ja.jsonl`
- `eval_extractors/extractor_generalization_ja.jsonl`
- `eval_extractors/oracle_replay_holdout_ja.jsonl`

## 9. Remaining unresolved items

- The AIKanojyo repository architecture was not available in this probe, so integration points are proposed rather than verified against AIKanojyo code.
- The current research docs still contain historical wording that calls Local Rule “planned” in older sections. This handover treats that as historical context and states the current verified code status.
- Formal AIKanojyo success criteria need real Shadow logs and response A/B evidence.
