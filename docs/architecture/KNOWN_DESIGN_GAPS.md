> 調査範囲: このリポジトリに存在する Trace Recall Engine のコードと同梱ドキュメントから確認した内容のみを記載する。AIKanojyo 本体の `ChatOrchestrator`、`MemoryRetrievalMerge`、`PromptInputModel`、`StructuredPromptBuilder` 等の実装コードはこのリポジトリでは未確認。未確認箇所は推測せず「未確認」とする。

# KNOWN_DESIGN_GAPS

事実のみを列挙する。改善案は記載しない。

* AIKanojyo 本体の `ChatOrchestrator`、`MemoryRetrievalMerge`、`RecallFact`、`PromptInputModel`、`StructuredPromptBuilder`、`Emotion`、`Relationship` 実装はこのリポジトリでは未確認。
* Trace Engine が `MemoryRetrievalMerge` に接続されている実装は未確認。
* Trace Engine が `RecallFact` 系へ接続されている実装は未確認。
* Prompt へ入る Trace 件数は Gate の `max_prompt_threads`、`max_prompt_words`、`max_core_words_per_thread` で制限されるが、RecallFact が 1 件かどうかは未確認。
* `build_response_prompt` は activation trace を default で Prompt 本文に入れず、「console log only」と表示する。
* `CandidateSpanGenerator` の terminal-boundary 候補は diagnostics 用で、local-rule selector の通常 final output には入らない。
* mixed-script promotion は `enable_mixed_script_promotion` が有効な場合のみ候補を追加する。
* Prompt 長は `prompt_stats` による概算表示はあるが、hard limit enforcement は未確認。
* `cmd_ask` は応答後に入力を Trace thread として保存しない。`cmd_chat` default path は ask 後に保存する。
* Shadow mode / production AIKanojyo prompt injection は同梱 integration guide 上の計画・推奨として存在するが、本リポジトリの production AIKanojyo 実装では未確認。
