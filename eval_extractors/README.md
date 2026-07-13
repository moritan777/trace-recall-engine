
## Extractor Generalization Benchmark

`extractor_core_ja.jsonl` is the development-facing Core Benchmark used to check the baseline extractor behavior while Local Rule v0 was being implemented. It should not be used as evidence that Local Rule v0 generalizes to unseen Japanese expressions.

`extractor_generalization_ja.jsonl` is the unseen-expression Generalization Benchmark. It contains 63 scenarios across identity variation, preference variation, time expressions, future plans, conversation bridges, boundaries, emotion, third-person references, unknown names, compound words, mixed script, colloquial wording, ellipsis, negation, correction, long chunks, short utterances, and participant references. The fixture intentionally includes unknown names, novel compounds, notation variation, and long chunks without adding those terms to the Local Rule dictionary.

Local Rule v0 is not adopted yet. Generalization results determine the next improvement scope; this benchmark is observational and should not be adjusted to match Local Rule internals.

## Oracle Replay Evaluator

Oracle Replay is an offline evaluator, not a production selector. It replays saved extractor Oracle details JSONL to compare fixed virtual selection strategies before implementation.

It does not alter Trace storage, Recall, or current extractor behavior. It does not change candidate generation, tokenization, gates, activation, working memory, or local-rule selection.

Its purpose is to estimate selector trade-offs before implementing them: expected-hit gain, word-count growth, unmatched added words, and counterexample risk. AIKanojyo integration remains the practical end goal; the next step after a useful replay result is to implement only the smallest promising extractor strategy and verify it downstream.

Dictionary coverage diagnostics keep DB vocabulary coverage separate from built-in protected patterns, mixed-script spans, dates, URLs, email, and other protected-span sources. If DB-derived protected matches are zero, DB dictionary coverage of zero is correct rather than a replay-adjusted score.
