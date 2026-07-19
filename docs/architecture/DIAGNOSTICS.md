> 調査範囲: このリポジトリに存在する Trace Recall Engine のコードと同梱ドキュメントから確認した内容のみを記載する。AIKanojyo 本体の `ChatOrchestrator`、`MemoryRetrievalMerge`、`PromptInputModel`、`StructuredPromptBuilder` 等の実装コードはこのリポジトリでは未確認。未確認箇所は推測せず「未確認」とする。

# DIAGNOSTICS

## Diagnostic ログ一覧

| ログ / 診断 | 出力場所 | 出力条件 | 用途 | 使う調査 |
|---|---|---|---|---|
| `LocalRuleTraceExtractor.last_diagnostics` | extractor instance | `extract` 実行ごと | 候補、final words、保護 span、辞書 hit、chunk accept/reject を確認 | 抽出品質調査 |
| `JapaneseTraceTokenizer.last_diagnostics` | tokenizer instance 経由で extractor diagnostics に merge | `tokenize` 実行ごと | primary chunks、alternate spans、split 数、長さを確認 | tokenizer 境界調査 |
| `CandidateSpanGenerator.last_diagnostics` | generator instance 経由で tokenizer diagnostics に merge | `generate` 実行ごと | mixed-script / terminal-boundary 候補数、limit、discard を確認 | v2 候補調査 |
| `print_activation` / `[Raw Activation]` | stdout | ask/chat/prompt-preview 実行時 | input words、activated words、activated threads、activation trace を可視化 | recall 経路調査 |
| `ActivationTrace` | `ActivationResult.traces`、stdout、任意で Prompt | activation 中 | word→thread→word、common bonus、mutual amplification の伝播ログ | TraceActivation 調査 |
| `print_gated_context` / `[Recall Selection]` | stdout | Gate 有効時 | selected ThreadGroup、selected words、suppressed words を確認 | Prompt 投入前の選別調査 |
| `[Conversation Fatigue]` | stdout | Gate 有効時 | fatigue による suppress を確認 | 反復露出・抑制調査 |
| `[Working Memory Candidate]` | stdout | Gate 有効時 | prompt に入る ThreadGroup/Words を確認 | WorkingMemory 候補調査 |
| `[LLM Prompt Stats]` | stderr | `ResponseGenerator.generate` 実行時 | prompt の概算 char/line/token count | prompt 長調査 |
| `[Prompt Size]` | stdout | `cmd_prompt_preview` 実行時 | trace あり/なし prompt size 比較 | Prompt A/B 事前確認 |
| extractor benchmark details | JSONL details path | `cmd_eval_extractor` 系 | expected hit、missing、unexpected、token diagnostics、oracle diagnostics | extractor benchmark |
| extractor benchmark report | Markdown report path | `cmd_eval_extractor` 系 | 集計サマリ | extractor regression |

## 指示書例にあるが未確認のログ

`MemoryRetrievalMerge`、`TraceRecallDiag`、`TraceActivationDiag`、`RecallFactPromptBridgeDiag`、`RecallFactUsageDiag`、`RecallBenchmarkTurnSummary`、`ConversationContinuity...` はこのリポジトリでは実装名として未確認。
