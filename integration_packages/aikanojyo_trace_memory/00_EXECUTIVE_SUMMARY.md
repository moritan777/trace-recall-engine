# Executive Summary

## Final purpose
AIKanojyoの既存Memoryを置き換えることではない。

会話からTraceを抽出し、Word / Thread / Connectionとして保存し、現在の入力から関連TraceをActivation・Selectionし、Working Memoryへ渡すExperimental Memory Pathを追加する。

## Current judgment
- Verified: Word/Thread/link storage, raw activation, gate, fatigue, prompt views exist in the Python prototype.
- Experimental: Local Rule Extractor and tokenizer are candidates for C# porting.
- Verified from project materials: long-run synthetic evaluation including 500T-class work was performed, but this package does not include benchmark logs.
- Experimental limitation: generalization drops; production evidence is insufficient.
- Planned: AIKanojyo should evaluate via Shadow Mode before any prompt use.

## First AIKanojyo steps
AIKanojyo Memory architecture監査 → 並列統合点決定 → Storage / Model追加 → Shadow Mode → Recall比較 → Prompt A/B.

## One-line design
Trace Memory stores recall cues, not summaries; the LLM reconstructs natural language from bounded, gated cue material.
