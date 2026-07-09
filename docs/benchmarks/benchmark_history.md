# Trace Recall Engine - Research History

## Purpose

This document records the chronological design shift behind the Trace Recall Engine benchmarks.

## Configuration

The history covers the 100T Weighted-vs-Count comparison and subsequent Count-mode evaluations at 1000T, 3000T, and 10000T.

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

Promptサイズは増加せず、Recall Precisionも高水準を維持。

ここで保存方式ではなく、Recall Selectionこそが重要な研究対象であることが明確になった。

↓

## 3000ターン評価

Recall Engine全体のスケーラビリティを評価。

Prompt Tokens、ThreadGroup数、Working Memoryサイズはいずれも安定。

長期化によるPrompt爆発は発生しなかった。

↓

## 10000ターン評価

10000ターン規模でも、ThreadGroup数、Promptサイズ、Recall Precision、Conversation Fatigueはいずれも安定。

Trace Recall Engineは、Conversation長ではなくWorking Memoryサイズでスケールすることを確認。

この結果により、長期会話を前提としたRecall Engineの基本設計が成立することを確認した。

↓

## Results

100TではCount方式の採用を決定し、1000T以降ではCount方式のままWorking Memoryを bounded に保てることを確認した。

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

RecallされたTraceから、Working Memoryへ何を載せるべきか

保存方式の研究は一区切りとなり、今後はRecall Selection・Working Memory Policy・Conversation Policyを中心とした研究へ移行する。

## Conclusion

Trace Recall Engineの研究対象は、Memory StorageからRecall Selection、Working Memory Policy、Conversation Policyへ移行した。
