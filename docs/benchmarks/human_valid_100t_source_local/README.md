# Human-Valid 100T Evaluation

## Purpose

This experiment evaluates whether Trace Recall produces
human-valid conversational responses.

It does not evaluate exact retrieval accuracy.

Recall may be:

- incomplete
- associative
- uncertain
- reconstructive

These properties are not automatically considered failures.

The primary failures of interest are:

- confident false memories
- incorrect attribution
- clear contradiction of established history

## Configuration

- Conversation: `eval_conversations/long_100t_mixed_recall.jsonl`
- Turns: 100
- Generated responses evaluated: 51
- Extractor: LLM
- Extractor model: `local-model`
- Response model: `local-model`
- Word policy: `identity`
- Prompt view: `threadgroup-source`
- Activation Gate: baseline
- `gate-cap-after-group`: disabled

## Human-Valid result

| Classification | Count |
|---|---:|
| Human-Valid | 48 |
| Human-Invalid | 2 |
| Undetermined | 1 |

Among determined responses:

**48 / 50 = 96.0% Human-Valid**

## Interpretation

The result should not be interpreted as 96% retrieval accuracy.

The objective of Trace Recall is not to reproduce stored information
with database-like precision.

Incomplete recall and uncertain associative reconstruction are allowed
when the resulting response remains conversationally plausible and
does not assert unsupported history as fact.

## Source-text observation

Selected ThreadGroups additionally exposed their verbatim
`source_text` to the response LLM.

No application-side semantic labels such as:

- subject
- preference
- causality
- temporal relation

were generated.

The application supplied stored traces and original utterances;
semantic interpretation remained the responsibility of the LLM.

The source-text condition improved several cases where a set of
isolated trace words had previously encouraged incorrect
reconstruction.

## Examples

### Preserved relation

Past utterances:

> のりこは紅茶が好き

> 前はコーヒーが好きだったけど、今日は紅茶も気になる

Providing the original utterances allowed the response model to
preserve these as separate memories instead of inventing a causal
relationship between them.

### Reconstructive recall

A response connecting movies, popcorn, and cafés may be acceptable
when expressed as an uncertain association rather than as a definite
historical event.

This distinction is intentional.

## Limitations

This is a **development-fixture result**.

`long_100t_mixed_recall.jsonl` was repeatedly inspected during
development, and individual failure cases influenced the research
direction.

The Human-Valid criterion was also refined during development.

Therefore this result must not be presented as an unseen benchmark
or general 96% performance claim.

The next evaluation should use a frozen configuration on an unseen
conversation fixture.