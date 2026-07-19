> 調査範囲: このリポジトリに存在する Trace Recall Engine のコードと同梱ドキュメントから確認した内容のみを記載する。AIKanojyo 本体の `ChatOrchestrator`、`MemoryRetrievalMerge`、`PromptInputModel`、`StructuredPromptBuilder` 等の実装コードはこのリポジトリでは未確認。未確認箇所は推測せず「未確認」とする。

# DEPENDENCY_MAP

## 確認できる依存図

`ChatOrchestrator` はこのリポジトリでは未確認。代替として、確認できる CLI orchestrator (`cmd_chat` / `cmd_ask`) からの依存を示す。

```mermaid
graph TD
  CLI[cmd_chat / cmd_ask / cmd_prompt_preview]
  Build[build_components]
  Store[ThreadedConceptMemoryStore]
  Factory[create_extractor]
  Extractor[TraceExtractor]
  Local[LocalRuleTraceExtractor]
  LLMExt[LLMTraceExtractor]
  Tok[JapaneseTraceTokenizer]
  Span[CandidateSpanGenerator]
  Norm[normalize_participant_references]
  Act[ActivationEngine]
  Gate[ActivationGate]
  Prompt[build_response_prompt]
  Format[format_gated_recall_context]
  Resp[ResponseGenerator]
  Chat[call_openai_compatible_chat]
  Fallback[fallback_generate_response]

  CLI --> Build
  Build --> Store
  Build --> Factory
  Factory --> Extractor
  Extractor --> Local
  Extractor --> LLMExt
  Local --> Tok
  Tok --> Span
  CLI --> Norm
  CLI --> Act
  Act --> Store
  CLI --> Gate
  Gate --> Store
  CLI --> Resp
  Resp --> Prompt
  Prompt --> Format
  Resp --> Chat
  Resp --> Fallback
  CLI --> Store
```

## ChatOrchestrator からの依存

未確認。
