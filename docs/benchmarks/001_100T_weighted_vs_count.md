# Benchmark 001 - 100T Weighted vs Count

## Purpose

Weighted方式とCount方式を比較し、Trace Recall Engineの保存方式を決める。

## Configuration

| Item | Count |
|---|---|
| Conversation | long_100t_mixed_recall.jsonl |
| Count DB | eval_long100_count.db |
| Weighted DB | eval_long100_weighted.db |
| Response Generation | enabled |
| Evaluation | Expected / Unexpected word matching |

## Results

| Mode | Expected Hits | Unexpected Hits | Fatigue Suppressed | Average Precision |
|---|---:|---:|---:|---:|
| Count | 110 | 5 | 11 | 0.958 |
| Weighted | 112 | 6 | 12 | 0.952 |

## Findings

Weighted方式とCount方式の差は小さかった。

Weighted方式は想定よりも安定しており、100Tでは破綻しなかった。

一方で、Count方式は「同じ経験をstrengthで潰す」のではなく、「経験の本数として残す」ため、Trace Recall Engineの設計思想とより整合する。

## Decision

Count方式を採用する。

Weighted方式は以後の主要評価対象から外す。

## Interpretation

この時点で重要だったのは、単純なPrecision差ではない。

Count方式が、経験の蓄積をより自然に表現できたことが採用理由である。
