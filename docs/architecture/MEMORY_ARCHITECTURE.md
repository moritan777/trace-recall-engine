> 調査範囲: このリポジトリに存在する Trace Recall Engine のコードと同梱ドキュメントから確認した内容のみを記載する。AIKanojyo 本体の `ChatOrchestrator`、`MemoryRetrievalMerge`、`PromptInputModel`、`StructuredPromptBuilder` 等の実装コードはこのリポジトリでは未確認。未確認箇所は推測せず「未確認」とする。

# MEMORY_ARCHITECTURE

| 種別 | 保存場所 | 生成タイミング | 利用タイミング | Promptとの関係 |
|---|---|---|---|---|
| Working Memory | 永続保存なし。`GatedContext` DTO。 | `ActivationGate.gate` 実行時。 | `build_response_prompt` で prompt-visible context として使用。 | `[Gated Recall Context]`, `[Gated Thread Groups]`, `[Gated Words]` に入る。 |
| Long Term Memory | AIKanojyo 本体は未確認。Trace Engine では SQLite の `threads` / `words` / `word_threads`。 | `create_thread` 実行時。 | activation、trace dictionary、一覧表示、fatigue 参照。 | Trace の場合、activation/gate を経由して入る。 |
| Embedding | 未確認 | 未確認 | 未確認 | 未確認 |
| Keyword | `words` table と `ExtractedWord`。 | extractor 実行時、commit 時。 | activation の input anchor、store vocabulary。 | `[Extracted Input Words]` と gated/activated words。 |
| Trace | `threads` と `word_threads`。 | `create_thread` 実行時。 | `ActivationEngine.activate` が word→thread→word を伝播。 | ThreadGroup / recall state / edge view として prompt 候補化。 |
| RecallFact | 未確認 | 未確認 | 未確認 | 未確認 |
| Conversation Context | `conversation_exposures` table は確認済み。AIKanojyo ConversationContext は未確認。 | gated context を prompt/response に露出した後。 | fatigue 判定。 | 過去露出回数により prompt-visible words を抑制。 |

## SQLite schema

Trace Engine は `words`、`threads`、`conversation_exposures`、`word_threads` を作成する。`threads.source_text` は debug/list 用として保持される。

## Trace dictionary

`LocalRuleTraceExtractor` は Store が `set_trace_vocabulary_provider` で注入されると、既存 Trace DB の vocabulary を保護 span として再利用する。別 dictionary DB は作らない。
