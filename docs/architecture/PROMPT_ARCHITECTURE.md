> 調査範囲: このリポジトリに存在する Trace Recall Engine のコードと同梱ドキュメントから確認した内容のみを記載する。AIKanojyo 本体の `ChatOrchestrator`、`MemoryRetrievalMerge`、`PromptInputModel`、`StructuredPromptBuilder` 等の実装コードはこのリポジトリでは未確認。未確認箇所は推測せず「未確認」とする。

# PROMPT_ARCHITECTURE

## 確認できる Prompt builder

このリポジトリの Prompt 生成は `build_response_prompt` と、その下位の `format_gated_recall_context` / `format_threadgroup_view` / `format_recall_state_view` / `format_edge_view` である。`PromptInputModel` と `StructuredPromptBuilder` は未確認。

| Section / 要素 | 取得元 | 関数 |
|---|---|---|
| Current Input | user input text | `build_response_prompt` |
| Extracted Input Words | `ActivationResult.input_words` | `build_response_prompt` |
| Participant reference note | 固定文 | `build_response_prompt` |
| Gated Recall Context | `GatedContext.summary` | `format_gated_recall_context` |
| Gated Thread Groups | `GatedContext.threads` | `format_threadgroup_view` |
| Gated Words | `GatedContext.words` | `format_threadgroup_view` |
| Suppressed Words | `GatedContext.suppressed_words` | `format_gated_recall_context` |
| Recall State | `GatedContext.threads` | `format_recall_state_view` |
| Edge Activation | `GatedContext.threads` | `format_edge_view` |
| Activated Words | `ActivationResult.activated_words` | `build_response_prompt` when no gated context |
| Activated Experience Threads | `ActivationResult.activated_threads` | `build_response_prompt` when no gated context |
| Activation Trace | `ActivationResult.traces` | omitted by default, included with flag |
| Instruction | 固定文 | `build_response_prompt` |
| Style | system message の「日本語で自然に短く」「返答は1〜3文」 | `ResponseGenerator.generate` |
| Emotion | 未確認 | 未確認 |
| Relationship | 未確認 | 未確認 |
| LongTermMemory | AIKanojyo 本体は未確認。Trace DB は Activation/Gate 経由。 | `ActivationEngine.activate` → `ActivationGate.gate` |
| ConversationContext | exposure/fatigue のみ確認。AIKanojyo ConversationContext は未確認。 | `ActivationGate.gate` |
| RecallRegenerationHint | 未確認 | 未確認 |

## Prompt 長

`prompt_stats` / `prompt_stats_dict` による概算 token/char/line count はあるが、hard limit enforce は未確認。
