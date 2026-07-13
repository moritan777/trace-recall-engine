# Current Research Direction

## Status

Trace Recall Engine is a research prototype. It stores traces rather than reconstructed meaning, activates broadly, selects carefully, keeps Working Memory bounded, and leaves meaning construction to the LLM. Remembering and speaking remain separate problems.

## What Has Been Confirmed

| Area | Confirmed | Not Yet Confirmed |
|---|---|---|
| Baseline storage | Count mode is the current Baseline. Weighted mode is retained only for historical comparison and compatibility. | Count mode is not proven superior for all domains or languages. |
| Scale | Public 100T, 1000T, 3000T, and 10000T evaluations were run. | These do not prove final conversation quality or superiority over other memory systems. |
| Working Memory | Working Memory and prompt size did not grow in proportion to total conversation length in the long benchmarks. | Behavior after extractor replacement and after real app integration remains Future Work. |
| Activation and Gate | Raw Activation and Gate selection are separated so activation can remain broad while Working Memory remains bounded. | The current thresholds are not final product defaults. |
| ThreadGroup | ThreadGroup compression reduced repeated experiences into compact prompt units. | ThreadGroup is not a semantic summary and is not final conversation policy. |
| Conversation Fatigue | Conversation Fatigue suppresses repeatedly exposed topics. | It does not prove natural long-term dialogue by itself. |
| Participant Reference Normalization | Experimental normalization maps first/second-person references according to `created_by`, adding `@user` and `@assistant` traces. | It does not fully solve all participant ambiguity and does not add identity-specific scoring. |
| Prompt View | Prompt View comparison infrastructure exists for `threadgroup`, `recall-state`, and `edge`. | No single Prompt View winner has been selected. |
| Sensitivity Framework | Numeric and categorical dimensions can be swept with reproducibility manifests. | Sensitivity reports are local generated artifacts unless explicitly committed. |
| Research Logger | Prompt/response research logs can be saved for `eval` and sensitivity runs. | Logs can contain private conversation content and should not be published blindly. |

## Largest Open Constraint: Trace Extraction

Current Trace Extraction is behind a replaceable extractor boundary. The default remains LLM-dependent when an endpoint is configured. This LLM Extractor is not a failure; it is useful as an Implemented research Baseline because it made rapid experimentation possible. However, it introduces important constraints:

- additional LLM calls
- communication and latency cost
- API and endpoint failure dependency
- model-dependent output variation
- non-deterministic extracted words
- possible bridge-word omissions such as missing a word that connects a name question to stored name traces
- poor fit for fully on-device use

Without an endpoint, or when `--extractor fallback` is selected, the current implementation uses an Implemented fallback Extractor path. That path is useful for diagnostics and basic operation, but it is not yet the selected production Extractor.

## Next Research Hypothesis

Trace Recall Engine may not require advanced semantic parsing at the extraction boundary. A slightly broader, deterministic local extraction method may preserve enough downstream recall quality to be useful.

This is a hypothesis, not an established result.

## Next Comparison Targets

- LLM Extractor — Implemented / Current Research Baseline
- Fallback Extractor — Implemented / diagnostic fallback
- Trace-specific Local Rule Extractor — Planned
- Morphological-analysis-assisted Extractor — Candidate / not selected

No Sudachi, MeCab, or custom-only approach has been selected yet.

## Evaluation Criteria

Extractor replacement should be judged by downstream recall, not by word-for-word agreement with the LLM Extractor. Candidate metrics include:

- expected hit
- unexpected hit
- precision-like
- empty extraction rate
- average extracted word count
- damaged token rate
- compound retention
- bridge-word retention
- extraction latency
- memory footprint
- dictionary / package size
- DB growth
- downstream prompt size

## Relationship to AIKanojyo

Trace Recall Engine is the generalizing recall research base. AIKanojyo is the first intended practical integration target.

The final goal is AIKanojyo integration, but this repository should first test whether the extraction boundary can be replaced while preserving downstream recall behavior. Android feasibility and conversation-quality evaluation after integration remain Future Work.

## Local Rule Extractor v0 Status

LLM Extractor is the current baseline; fallback remains a diagnostic path. Local Rule Extractor v0 is now an experimental deterministic local candidate: it uses no morphological analyzer, no external API, and is not integrated with Android yet.
