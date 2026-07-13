# Dynamic Trace Dictionary

The local-rule extractor can protect spans by using words that already exist in the Trace DB as a dynamic vocabulary mirror.

## No Additional DB

This feature does not create a dictionary database, vocabulary database, trie database, JSON cache, or secondary SQLite file. The only source of truth is the existing `words` table in the current Trace DB. The in-memory vocabulary is a disposable mirror and is invalidated after new words are saved.

## Protected Span Detection

Pipeline order:

1. Surface normalize.
2. Detect protected spans.
3. Coarse/chunk split only on residual text outside protected spans.
4. Apply local rules.
5. Residual split.
6. Noise filter.
7. Participant-reference normalization.

Protected spans include:

- existing Trace DB words,
- katakana runs,
- mixed alphanumeric/Japanese terms,
- dates,
- URLs,
- email addresses,
- existing built-in bridge/time/action terms.

## Longest Match

When vocabulary entries overlap at the same location, the extractor keeps only the longest non-overlapping span. For example, if the DB contains `AI`, `AIKanojyo`, and `AIKanojyo Project`, then `AIKanojyo Projectを作る` protects `AIKanojyo Project` instead of splitting at `AI`.

## Usage-Weighted Priority

The dynamic vocabulary keeps DB words with `length >= 2` and excludes stop words and punctuation-only entries. It scores candidates from existing DB metadata:

```text
score = weight × frequency boost × time decay
```

The score only prioritizes which existing words are protected; it does not learn a new dictionary and does not perform recall, embedding search, LLM inference, morphology, or part-of-speech estimation.

## Cache Behavior

The store loads words from SQLite on first vocabulary access, keeps them in memory for extractor calls, and invalidates the mirror after `create_thread` saves or reinforces words. This avoids scanning SQLite on every extraction while preserving the DB as the only source of truth.

## Evaluation Metrics

Extractor evaluation rows now include:

- `protected_match_count`,
- `protected_match_length`,
- `db_dictionary_hit_rate`,
- `longest_match_success`,
- `dictionary_coverage`.
