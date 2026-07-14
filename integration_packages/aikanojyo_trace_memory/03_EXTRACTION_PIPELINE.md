# Extraction Pipeline

## Contract
Input: text, role/created_by, existing Trace vocabulary. Current Python TraceExtractor.extract accepts text; created_by is applied by participant reference normalization outside extractor. Output: ExtractedWord list plus diagnostics on LocalRuleTraceExtractor.last_diagnostics.

## Order
Normalize → Protected Span → JapaneseTraceTokenizer → CandidateSpanGenerator diagnostics → Local Rule selection → Dedupe → Participant Reference Normalization.

## Local Rule purpose
Experimental deterministic trace-cue extractor, not a morphological analyzer. It favors useful recall chunks over perfect boundaries, avoids external dependencies, and preserves deterministic order.

## Protected spans
Trace vocabulary longest matches, built-in bridge/time/action words, URL, email, date, mixed script, and selected compounds.

## CandidateSpanGenerator
- mixed-script: diagnostic; can be promoted only when enable_mixed_script_promotion=True.
- terminal-boundary: diagnostic only.
- general alternates: diagnostic only.

## Participant Reference
Separate from extractor. created_by determines whether first/second-person references produce @user or @assistant. Do not show internal markers to users.

## Do not do
Do not add person/product dictionaries, unbounded rules, always-on LLM extraction, Sudachi/MeCab by default, or aggressive lemmatization.
