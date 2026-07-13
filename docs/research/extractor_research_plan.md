# Extractor Research Plan

This document is a pre-implementation research plan. It does not describe an implemented local Extractor.

## Scope

### Boundary introduced in Phase 1

- A common Extractor contract is defined in `src/trace_recall/extractors/base.py`.
- The existing LLM Extractor is split into `src/trace_recall/extractors/llm.py`.
- The existing fallback Extractor is split into `src/trace_recall/extractors/fallback.py`.
- `src/trace_recall/extractors/factory.py` creates extractors from CLI configuration.
- `src/trace_recall/extractors/local_rule.py` is only a placeholder for the future deterministic Trace-specific extractor.

### Planned for the next Extractor research phase

- Implement a local-rule candidate.
- Compare Extractors through the same downstream recall pipeline.
- Run PC evaluation first.
- Prepare for future Android device evaluation.

### Not planned for the immediate phase

- Separate this work into another repository.
- Immediately integrate into AIKanojyo itself.
- Decide immediately on Sudachi, MeCab, or any specific morphological analyzer.
- Add a Knowledge Layer.
- Remove the LLM Extractor.
- Change production defaults.

## Proposed Module Boundary

The Phase 1 module boundary is implemented as:

```text
src/
├── threaded_concept_memory_probe.py
└── trace_recall/
    └── extractors/
        ├── __init__.py
        ├── base.py
        ├── llm.py
        ├── fallback.py
        ├── local_rule.py
        └── factory.py
```

The engine now obtains an extractor from the factory and calls `extractor.extract(text)`. Participant Reference Normalization remains outside the extractor boundary.

## Extraction Boundary

The intended boundary is:

```text
Original utterance
→ Extractor
→ Participant Reference Normalizer
→ Thread creation
→ Recall pipeline
```

Participant Reference Normalization should remain outside the Extractor because it depends on speaker origin (`created_by`) and conversation participant roles. The Extractor should produce candidate trace words from the utterance; it should not decide whether `私` means `@user` or `@assistant`. Keeping this boundary separate makes Extractor comparison fair and keeps participant policy testable as a feature-ablation dimension.

## Success Criteria

Thresholds are provisional and should be set after baseline measurement. Candidate success criteria are:

- downstream recall quality degrades only within an acceptable range
- empty extraction is rare
- person names, compounds, dates, and emotion words are not damaged
- bridge words are retained often enough for recall scenarios
- extraction is deterministic
- no additional LLM call is required
- latency and memory footprint are compatible with future Android integration
- DB growth and downstream prompt size remain controlled

## Comparison Method

The comparison should hold Trace Memory, Raw Activation, Recall Selection, Working Memory, Prompt View, and evaluation scenarios fixed where possible. The measured question is not whether a local Extractor exactly matches the LLM Extractor, but whether the recall pipeline still surfaces the expected traces.
