# Working Memory and Prompt

## Working Memory is cue material
It is not finalized semantic prose. It contains words, ThreadGroups, origin/created_by counts, source cues, scores, roles, and suppression diagnostics.

## Prompt views (Verified)
- threadgroup: current baseline; canonical groups with direct/core/support words.
- recall-state: more compact state view; can group by origin.
- edge: word-edge count view.

## Recommended prompt instruction
以下は会話中に反応した記憶の痕跡です。事実として断定できる範囲だけ使ってください。質問に直接答えてください。内部ラベルや活性化状態を説明しないでください。分からない場合は推測しないでください。

## AIKanojyo integration caution
Do not place Trace above persona/boundary rules; do not collide with CanonicalUserName, Relationship, Dream, or Emotion systems; treat Trace as material layer only.

## Hide internal terms
Never expose @user, @assistant, thread_id, score, activation, fatigue, or canonical_key in final user-facing responses.
