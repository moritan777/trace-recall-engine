# Trace Recall Engine - Research History

## Purpose

This document records the chronological design shift behind the Trace Recall Engine benchmarks.

## Configuration

The history covers the 100T Weighted-vs-Count comparison, subsequent Count-mode evaluations at 1000T, 3000T, and 10000T, and the 100T Human-Valid evaluation of source-text-assisted recall.

## 2026-07-06

Weighted方式とCount方式の比較を開始。

当初は Thread Strength を数値で強化する Weighted方式 を想定していた。

↓

## 100ターン評価

Weighted方式とCount方式を比較。

Recall Precisionの差は僅差。

一方で、Count方式は「経験の本数が増える」という設計思想を自然に表現できることを確認。

↓

Count方式を正式採用。

Thread Strengthではなく、Experience Threadの蓄積によって想起強度を表現する方針へ移行。

↓

## ThreadGroup導入

同一ExperienceをWorking Memoryへ重複して渡さないよう、ThreadGroupを導入。

Count方式でもPromptサイズが増えない構造を確立。

↓

## Activation Gate導入

内部では広く励起し、Working Memoryへ渡す際に必要なExperienceだけを選択する層を追加。

「思い出す」と「現在考える」を分離。

↓

## Conversation Fatigue導入

RecallとConversationを分離。

強く想起できる記憶でも、直近で何度も話題に出ていればPromptから抑制する仕組みを追加。

「思い出すこと」と「話すこと」は別であることを設計へ反映。

↓

## Explainable Recall

Activation Traceをログとして可視化。

Input → Word → Thread → Word → Thread

という想起経路を説明可能にした。

「なぜその記憶が選ばれたのか」を追跡できるRecall Engineとなる。

↓

## 1000ターン評価

ThreadGroup、Activation Gate、Conversation Fatigueを含めた状態で1000ターン評価を実施。

Promptサイズは増加せず、no-response評価におけるWorking Memory候補のprecision-like指標も高水準を維持。最終LLM応答の精度を測定したものではない。

ここで保存方式ではなく、Recall Selectionこそが重要な研究対象であることが明確になった。

↓

## 3000ターン評価

Recall Engine全体のスケーラビリティを評価。

Prompt Tokens、ThreadGroup数、Working Memoryサイズはいずれも安定。

長期化によるPrompt爆発は発生しなかった。

↓

## 10000ターン評価

10000ターン規模でも、ThreadGroup数、Promptサイズ、Working Memory候補のprecision-like指標、Conversation Fatigueはいずれも安定。no-response評価のため、最終LLM応答の精度とresponse-aware Recall Efficiencyは評価対象外。

Trace Recall Engineは、Conversation長ではなくWorking Memoryサイズでスケールすることを確認。

この結果により、no-responseの範囲で長期会話を前提としたRecall / Working Memoryの基本設計が安定していることを確認した。最終応答品質の成立を示すものではない。

↓

## 2026-11-25 — Human-Valid 100T source-text evaluation

固定された100ターンのdevelopment fixtureを使い、最終応答が人間の会話として破綻していないかを評価した。

この評価はRAG型の厳密な検索精度ではなく、不完全・連想的・再構成的な想起を許容しながら、明確な偽記憶、人物の誤帰属、既知履歴との明確な矛盾を検出することを目的とする。

評価構成:

- LLM Extractor
- baseline Activation Gate
- `threadgroup-source` Prompt View
- local response model
- `gate-cap-after-group`: disabled

選択済みThreadGroupについて、保存済みの原文 `source_text` をResponse LLMへ渡した。

アプリ側では主語、好み、因果関係、時間関係などの意味ラベルを生成せず、意味解釈はLLMへ委ねた。

51応答をレビューした結果:

- Human-Valid: 48
- Human-Invalid: 2
- Undetermined: 1
- 判定可能50件中のHuman-Valid率: **48 / 50 = 96.0%**

`source_text` の提示により、単語集合だけでは失われていた発話内の関係をLLMが読み取れるケースを確認した。

一方、曖昧な連想や関連記憶の混合は、確定的な過去事実として断定しない限り、必ずしも失敗としない評価方針を採用した。

この結果は繰り返し確認・調整に使用したdevelopment fixture上の結果であり、未見benchmarkや一般的な96%のRecall精度を示すものではない。

次の評価では、構成をfreezeしたうえで未見conversation fixtureを一度だけ実行する。

詳細: [Human-Valid 100T Evaluation](human_valid_100t_source_local/README.md)

行単位評価: [human_valid.csv](human_valid_100t_source_local/human_valid.csv)

↓

## Results

100TではCount方式の採用を決定し、1000T以降ではCount方式のままWorking Memoryを bounded に保てることを確認した。

その後の100T Human-Valid評価では、選択済みThreadGroupへ原文 `source_text` を添える構成により、51応答中48件をHuman-Valid、2件をHuman-Invalid、1件をUndeterminedと判定した。

## Findings

Weighted方式は100Tでは破綻しなかったが、Experience Threadの蓄積を自然に表現するCount方式のほうが設計思想に合致した。

ThreadGroup、Activation Gate、Conversation Fatigueにより、保存されたTrace量とPromptへ渡すWorking Memory量を分離できた。

## Interpretation

初期:

AIはどう保存するか

↓

中期:

AIはどう思い出すか

↓

現在:

RecallされたTraceから、Working Memoryへ何を載せ、LLMがそれをどのように会話として再構成するか

保存方式の研究は一区切りとなり、現在はRecall Selection・Working Memory Policy・Conversation Policyに加えて、正確なRAG検索とは異なるHuman-Validな想起評価を研究対象としている。

## Conclusion

Trace Recall Engineの研究対象は、Memory StorageからRecall Selection、Working Memory Policy、Conversation Policy、そして不完全な想起からHuman-Validな応答を成立させる評価へ移行した。

今回の96.0%はdevelopment fixture上のチェックポイントであり、次の研究段階はfreezeした構成による未見fixture評価である。
