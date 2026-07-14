# Recall Pipeline

## Entry words
Current input is extracted into ExtractedWord items; participant references may be appended.

## Raw activation (Verified)
The prototype propagates Word→Thread→Word up to configured depth. Scores use input weight, link weight, node strength, thread effective strength, depth decay, recency/half-life, common activation bonus when multiple direct words support a thread, and same canonical-key count strength.

## ThreadGroup
Storage keeps independent threads. Gate groups only prompt-visible traces by canonical_key to avoid duplicate prompt content while preserving repeated-experience strength.

## Selection/Gate
ActivationGate has max_prompt_threads, max_core_words_per_thread, max_prompt_words, min_thread_score, min_word_score, fatigue_recent_turns, and fatigue_threshold.

## Fatigue
Recent prompt/response exposures suppress presentation, not recall or storage. Direct asked words can override suppression.

## Failure modes
popular word dominance, unrelated spread, empty recall, wrong participant, stale repeated memory, mixed-script miss, correction conflict, and negation reconstruction risk.
