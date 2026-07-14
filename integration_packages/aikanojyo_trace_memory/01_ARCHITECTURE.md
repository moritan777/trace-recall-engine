# Architecture

## Conceptual architecture
Conversation → Trace Extraction → Word / Thread / Connection → Raw Activation → Recall Selection → Gate / Fatigue → Working Memory → Prompt → LLM Response.

## Parallel AIKanojyo integration
```text
                    ┌─────────────────────────┐
Conversation ──────▶│ Existing AIKanojyo Path │──▶ Production Prompt
                    └─────────────────────────┘
           │
           └────────▶ Trace Memory Shadow Path
                      ├─ Extract
                      ├─ Store
                      ├─ Recall
                      └─ Diagnostics only
```

## Experimental after Shadow
Existing Working Memory + Trace Working Memory → Prompt A/B. Default remains OFF.

## Responsibilities
- Extractor: generate Trace candidates.
- Normalizer: normalize text and words.
- Participant Reference: add @user/@assistant from created_by and utterance pronouns.
- Store: save Word, Thread, and word_threads links.
- Activation: broad Word→Thread→Word spread.
- Selection/Gate: choose bounded prompt-visible groups and words.
- Fatigue: suppress recently exposed topics without deleting memory.
- Prompt Builder: present cue material; do not demand graph explanations from LLM.
- LLM: compose meaning and natural response.
